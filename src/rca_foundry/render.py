from __future__ import annotations

from html import escape

import markdown


REPORT_STYLES = """
body {
  margin: 0;
  background: #f8fafc;
  color: #0f172a;
  font-family: Arial, Helvetica, sans-serif;
}
main {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px 48px;
}
article {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}
h1, h2, h3 {
  color: #0f172a;
}
h1 {
  margin-top: 0;
}
code {
  background: #e2e8f0;
  border-radius: 4px;
  padding: 0.15em 0.35em;
}
pre {
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  overflow-x: auto;
}
table {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
}
th, td {
  border: 1px solid #cbd5e1;
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #e2e8f0;
}
blockquote {
  border-left: 4px solid #94a3b8;
  margin-left: 0;
  padding-left: 16px;
  color: #334155;
}
"""


def render_markdown_document(markdown_text: str, title: str) -> str:
    body_html = markdown.markdown(
        markdown_text,
        extensions=["extra", "tables", "fenced_code", "sane_lists"],
    )
    escaped_title = escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>{REPORT_STYLES}</style>
</head>
<body>
  <main>
    <article>
      {body_html}
    </article>
  </main>
</body>
</html>
"""
