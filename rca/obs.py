"""Langfuse observability wrapper for RCA pipeline runs.

Usage pattern:
    observer = RcaObserver(store_alias, dt, run_name, is_dry_run)
    client_factory = observer.wrap_client_factory(base_factory)
    with observer.node_span("plan"):
        ...
    observer.finalize(output={"decision": ...})

Completely no-op when Langfuse env vars are absent or is_dry_run is True.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Callable, Generator

ClientFactory = Callable[[str], Any]


# ---------------------------------------------------------------------------
# No-op stubs (used when Langfuse is not configured)
# ---------------------------------------------------------------------------


class _NoopSpan:
    def end(self, **kwargs: Any) -> None:
        pass


@contextmanager
def _noop_cm() -> Generator[None, None, None]:
    yield


# ---------------------------------------------------------------------------
# Traced OpenAI-compatible client
# ---------------------------------------------------------------------------


class _TracedCompletions:
    def __init__(self, completions: Any, observer: "RcaObserver", node_name: str) -> None:
        self._completions = completions
        self._observer = observer
        self._node_name = node_name

    def create(self, **kwargs: Any) -> Any:
        model = kwargs.get("model", "unknown")
        messages = kwargs.get("messages", [])
        gen = self._observer._start_generation(self._node_name, model, messages)
        try:
            response = self._completions.create(**kwargs)
            output = ""
            if response.choices:
                output = response.choices[0].message.content or ""
            if gen is not None:
                update_kwargs: dict[str, Any] = {"output": output}
                if hasattr(response, "usage") and response.usage:
                    update_kwargs["usage"] = {
                        "input": getattr(response.usage, "prompt_tokens", 0),
                        "output": getattr(response.usage, "completion_tokens", 0),
                        "total": getattr(response.usage, "total_tokens", 0),
                    }
                if hasattr(response, "model") and response.model:
                    update_kwargs["model"] = response.model
                gen.update(**update_kwargs)
                gen.end()
            return response
        except Exception as exc:
            if gen is not None:
                gen.update(level="ERROR", status_message=str(exc))
                gen.end()
            raise


class _TracedChat:
    def __init__(self, chat: Any, observer: "RcaObserver", node_name: str) -> None:
        self.completions = _TracedCompletions(chat.completions, observer, node_name)


class _TracedClient:
    """Thin wrapper around an OpenAI-compatible client that logs LLM calls to Langfuse."""

    def __init__(self, client: Any, observer: "RcaObserver", node_name: str) -> None:
        self._client = client
        self.chat = _TracedChat(client.chat, observer, node_name)


# ---------------------------------------------------------------------------
# Observer
# ---------------------------------------------------------------------------


class RcaObserver:
    """Langfuse trace for one RCA run. No-op when env vars are absent."""

    def __init__(
        self,
        store_alias: str,
        dt: str,
        run_name: str,
        is_dry_run: bool = False,
    ) -> None:
        self._active = False
        self._lf: Any = None
        self._root_span: Any = None
        self._trace_id: str | None = None
        self._root_span_id: str | None = None

        if is_dry_run:
            return

        base_url = os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST")
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        if not (base_url and public_key and secret_key):
            return

        try:
            from langfuse import Langfuse

            self._lf = Langfuse(
                base_url=base_url,
                public_key=public_key,
                secret_key=secret_key,
            )
            self._root_span = self._lf.start_observation(
                name="rca_run",
                as_type="span",
                input={"store_alias": store_alias, "dt": dt},
                metadata={"run_name": run_name},
            )
            self._trace_id = self._root_span.trace_id
            self._root_span_id = self._root_span.id
            self._active = True
        except Exception:
            # Never crash the pipeline due to observability failures
            self._active = False

    # ------------------------------------------------------------------
    # Public interface for graph nodes
    # ------------------------------------------------------------------

    def node_span(self, node_name: str, **metadata: Any):  # type: ignore[return]
        """Context manager that creates a child span for a single graph node."""
        if not self._active:
            return _noop_cm()
        return self._active_node_span_cm(node_name, metadata)

    @contextmanager
    def _active_node_span_cm(
        self, node_name: str, metadata: dict[str, Any]
    ) -> Generator[Any, None, None]:
        from langfuse.types import TraceContext

        span = self._lf.start_observation(
            name=node_name,
            as_type="span",
            metadata=metadata or None,
            trace_context=TraceContext(
                trace_id=self._trace_id,  # type: ignore[arg-type]
                parent_span_id=self._root_span_id,
            ),
        )
        try:
            yield span
        finally:
            span.end()

    def wrap_client_factory(self, factory: ClientFactory) -> ClientFactory:
        """Return a factory whose clients log each chat.completions.create() call."""
        if not self._active:
            return factory

        observer = self

        def traced_factory(node_name: str) -> Any:
            client = factory(node_name)
            return _TracedClient(client, observer, node_name)

        return traced_factory

    def finalize(self, output: dict[str, Any] | None = None) -> None:
        """End the root span and flush all events to Langfuse."""
        if not self._active:
            return
        try:
            if self._root_span is not None:
                if output is not None:
                    self._root_span.update(output=output)
                self._root_span.end()
            if self._lf is not None:
                self._lf.flush()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_generation(
        self,
        node_name: str,
        model: str,
        messages: list[dict[str, Any]],
    ) -> Any | None:
        if not self._active:
            return None
        try:
            from langfuse.types import TraceContext

            return self._lf.start_observation(
                name=node_name,
                as_type="generation",
                model=model,
                input=messages,
                trace_context=TraceContext(
                    trace_id=self._trace_id,  # type: ignore[arg-type]
                    parent_span_id=self._root_span_id,
                ),
            )
        except Exception:
            return None
