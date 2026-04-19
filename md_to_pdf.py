#!/usr/bin/env python3
"""Convert markdown files to styled PDF using chromium headless.

Usage:
    python3 md_to_pdf.py input.md [output.pdf]

If output.pdf is omitted, writes to input.pdf (same name, .pdf extension).
No external Python dependencies — uses only stdlib + chromium.
"""

import os
import re
import subprocess
import sys
import tempfile

# ── Markdown to HTML ──

def _md_to_html(md: str) -> str:
    """Convert markdown to HTML. Handles headers, bold, italic, code blocks,
    tables, blockquotes, lists, horizontal rules, and blank answer lines."""
    lines = md.split("\n")
    html_lines = []
    in_code = False
    in_table = False
    in_ul = False
    in_ol = False
    in_blockquote = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Code blocks
        if line.strip().startswith("```"):
            if in_code:
                html_lines.append("</code></pre>")
                in_code = False
            else:
                html_lines.append("<pre><code>")
                in_code = True
            i += 1
            continue
        if in_code:
            html_lines.append(_esc(line))
            i += 1
            continue

        stripped = line.strip()

        # Blank line — close open lists/blockquotes
        if not stripped:
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            if in_ol:
                html_lines.append("</ol>")
                in_ol = False
            if in_blockquote:
                html_lines.append("</blockquote>")
                in_blockquote = False
            if in_table:
                html_lines.append("</table>")
                in_table = False
            html_lines.append("")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}$|^\*{3,}$|^_{3,}$", stripped):
            html_lines.append("<hr>")
            i += 1
            continue

        # Headers
        m = re.match(r"^(#{1,6})\s+(.*)", stripped)
        if m:
            level = len(m.group(1))
            text = _inline(m.group(2))
            html_lines.append(f"<h{level}>{text}</h{level}>")
            i += 1
            continue

        # Table row
        if "|" in stripped and stripped.startswith("|"):
            # Skip separator rows like |---|---|
            if re.match(r"^\|[\s\-:|]+\|$", stripped):
                i += 1
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not in_table:
                html_lines.append('<table>')
                tag = "th"
                in_table = True
            else:
                tag = "td"
            row = "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells)
            html_lines.append(f"<tr>{row}</tr>")
            i += 1
            continue

        # Close table if we're no longer in one
        if in_table and "|" not in stripped:
            html_lines.append("</table>")
            in_table = False

        # Blockquote
        if stripped.startswith(">"):
            text = _inline(stripped.lstrip("> "))
            if not in_blockquote:
                html_lines.append("<blockquote>")
                in_blockquote = True
            html_lines.append(f"<p>{text}</p>")
            i += 1
            continue

        # Unordered list
        m = re.match(r"^[\-\*]\s+(.*)", stripped)
        if m:
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1
            continue

        # Ordered list
        m = re.match(r"^\d+[\.\)]\s+(.*)", stripped)
        if m:
            if not in_ol:
                html_lines.append("<ol>")
                in_ol = True
            html_lines.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1
            continue

        # Details/summary (passthrough)
        if stripped.startswith("<details") or stripped.startswith("</details") or \
           stripped.startswith("<summary") or stripped.startswith("</summary"):
            html_lines.append(stripped)
            i += 1
            continue

        # Blank writing space (&nbsp; lines for printable worksheets)
        if stripped in ("&nbsp;", "&amp;nbsp;"):
            html_lines.append('<div class="writing-line"></div>')
            i += 1
            continue

        # Regular paragraph
        html_lines.append(f"<p>{_inline(stripped)}</p>")
        i += 1

    # Close any open blocks
    if in_ul:
        html_lines.append("</ul>")
    if in_ol:
        html_lines.append("</ol>")
    if in_blockquote:
        html_lines.append("</blockquote>")
    if in_table:
        html_lines.append("</table>")
    if in_code:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


def _esc(text: str) -> str:
    """Escape HTML entities."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    """Process inline markdown: bold, italic, code, links, underscores (answer blanks)."""
    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # Bold + italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Images: ![alt](path). Pick CSS class by filename prefix:
    #   section_*  → large centered section scene-setter (1:1)
    #   exercise_* → smaller right-floated companion per exercise (5:3, 1280x768)
    #   anything else (diagram_*, illust_*, mentor_hero_*) → default .illustration
    def _img_sub(m: "re.Match[str]") -> str:
        alt, src = m.group(1), m.group(2)
        base = os.path.basename(src)
        if base.startswith("section_"):
            cls = "illustration illustration-section"
        elif base.startswith("exercise_"):
            cls = "illustration illustration-exercise"
        else:
            cls = "illustration"
        return f'<img src="{src}" alt="{alt}" class="{cls}">'
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _img_sub, text)
    # Answer blanks (3+ underscores)
    text = re.sub(r"_{3,}", '<span class="blank">__________</span>', text)
    return text


CSS = """
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    max-width: 7.5in;
    margin: 0.5in auto;
    padding: 0;
    font-size: 12pt;
    line-height: 1.5;
    color: #1a1a1a;
}
h1 { font-size: 20pt; border-bottom: 2px solid #2563eb; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 16pt; color: #1e40af; margin-top: 24px; }
h3 { font-size: 13pt; color: #374151; }
p { margin: 6px 0; }
blockquote {
    border-left: 3px solid #2563eb;
    margin: 8px 0;
    padding: 4px 16px;
    background: #f0f7ff;
    font-size: 13pt;
}
pre {
    background: #f3f4f6;
    padding: 10px 14px;
    border-radius: 4px;
    font-size: 10pt;
    overflow-x: auto;
}
code { background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-size: 10pt; }
pre code { background: none; padding: 0; }
table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    font-size: 11pt;
}
th, td {
    border: 1px solid #d1d5db;
    padding: 6px 10px;
    text-align: left;
}
th { background: #eff6ff; font-weight: 600; }
tr:nth-child(even) td { background: #f9fafb; }
hr { border: none; border-top: 1px solid #d1d5db; margin: 20px 0; clear: both; }
ul, ol { margin: 6px 0; padding-left: 24px; }
li { margin: 3px 0; }
.blank {
    display: inline-block;
    min-width: 150px;
    border-bottom: 1px solid #6b7280;
    color: transparent;
}
.writing-line {
    height: 24px;
    border-bottom: 1px solid #e5e7eb;
    margin: 0;
}
.illustration {
    display: block;
    max-width: 70%;
    height: auto;
    margin: 12px auto;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
}
/* Large square scene-setter at the top of each section — centered, prominent. */
.illustration-section {
    max-width: 80%;
    margin: 16px auto 20px;
    border-radius: 6px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    break-inside: avoid;
}
/* Wide companion image per exercise — smaller so it doesn't dominate the page.
   Floats right with text wrapping around it; clears on horizontal rules so it
   never bleeds into the next problem. */
.illustration-exercise {
    max-width: 42%;
    float: right;
    margin: 4px 0 8px 16px;
    border-radius: 4px;
    break-inside: avoid;
}
@media print {
    body { margin: 0; }
    h1, h2 { break-after: avoid; }
}
"""


def convert(md_path: str, pdf_path: str | None = None) -> str:
    """Convert a markdown file to PDF. Returns the output PDF path."""
    if pdf_path is None:
        pdf_path = re.sub(r"\.md$", ".pdf", md_path)
        if pdf_path == md_path:
            pdf_path = md_path + ".pdf"

    with open(md_path, "r") as f:
        md_text = f.read()

    body_html = _md_to_html(md_text)
    full_html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body, {{delimiters:[
    {{left:'$$',right:'$$',display:true}},
    {{left:'$',right:'$',display:false}},
    {{left:'\\\\[',right:'\\\\]',display:true}},
    {{left:'\\\\(',right:'\\\\)',display:false}}
  ], throwOnError:false}});"></script>
<style>{CSS}</style>
</head><body>
{body_html}
</body></html>"""

    # Resolve relative image paths to absolute file:// URIs for chromium
    md_dir = os.path.abspath(os.path.dirname(md_path))
    def _abs_img(m):
        src = m.group(1)
        if not src.startswith(("http://", "https://", "file://", "/")):
            src = f"file://{os.path.join(md_dir, src)}"
        return f'src="{src}"'
    full_html = re.sub(r'src="([^"]+)"', _abs_img, full_html)

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
        f.write(full_html)
        html_path = f.name

    try:
        result = subprocess.run(
            [
                "chromium", "--headless", "--disable-gpu", "--no-sandbox",
                "--run-all-compositor-stages-before-draw",
                "--disable-software-rasterizer",
                "--allow-file-access-from-files",
                "--virtual-time-budget=15000",
                f"--print-to-pdf={os.path.abspath(pdf_path)}",
                f"file://{html_path}",
            ],
            capture_output=True, text=True, timeout=60,
        )
        if not os.path.exists(pdf_path):
            print(f"ERROR: chromium failed to create PDF\n{result.stderr}", file=sys.stderr)
            sys.exit(1)
    finally:
        os.unlink(html_path)

    size = os.path.getsize(pdf_path)
    print(f"Created {pdf_path} ({size:,} bytes)")
    return pdf_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} input.md [output.pdf]", file=sys.stderr)
        sys.exit(1)
    md_file = sys.argv[1]
    pdf_file = sys.argv[2] if len(sys.argv) > 2 else None
    convert(md_file, pdf_file)
