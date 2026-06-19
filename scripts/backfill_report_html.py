from __future__ import annotations

from pathlib import Path

from rca_foundry.config import AGENT_BENCHMARK_PATH
from rca_foundry.render import render_markdown_document


def _html_title_from_path(path: Path) -> str:
    if path.name == "report.md":
        return f"RCA report for {path.parent.name}"
    return f"{path.stem} memo for {path.parent.parent.name}"


def main() -> None:
    markdown_paths = sorted(AGENT_BENCHMARK_PATH.glob("**/*.md"))
    generated = 0
    for markdown_path in markdown_paths:
        if markdown_path.name == "README.md":
            continue
        if markdown_path.parent.name == "logs":
            continue
        html_path = markdown_path.with_suffix(".html")
        html_path.write_text(
            render_markdown_document(
                markdown_path.read_text(encoding="utf-8"),
                title=_html_title_from_path(markdown_path),
            ),
            encoding="utf-8",
        )
        generated += 1
    print(f"Generated {generated} HTML files under {AGENT_BENCHMARK_PATH}")


if __name__ == "__main__":
    main()
