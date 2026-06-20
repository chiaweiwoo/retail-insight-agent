from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="store-era test (context pack schema) — rewritten for city grain in Round E1")

from pathlib import Path

from rca.context import build_context_pack, build_context_preamble


def test_build_context_pack_writes_outputs(tmp_path) -> None:
    output_path = tmp_path / "context_pack.json"
    pack = build_context_pack(output_path=output_path)
    assert pack["dataset"]["stores"] == 15
    assert output_path.exists()
    assert output_path.with_suffix(".md").exists()


def test_context_preamble_mentions_opaque_ids_and_avoids_tier_claim() -> None:
    preamble = build_context_preamble("h555", "2024-05-16")
    assert "opaque anonymized identifiers" in preamble
    assert "not a documented tier" in preamble
    assert "Analysis date: 2024-05-16." in preamble
