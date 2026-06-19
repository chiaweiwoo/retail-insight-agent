from __future__ import annotations

from rca_foundry.render import render_markdown_document


def test_render_markdown_document_creates_html_shell() -> None:
    html = render_markdown_document("# Title\n\n- item", title="Demo")
    assert "<html" in html
    assert "<h1>Title</h1>" in html
    assert "<li>item</li>" in html
    assert "<title>Demo</title>" in html
