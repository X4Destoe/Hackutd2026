"""Render the reports' own (constrained) Markdown to a printable HTML page. Everything is HTML-escaped first, so text from
data (building names, alert headlines, LLM narrative) can never inject markup."""
from __future__ import annotations

import html
import re

CSS = """
*{box-sizing:border-box}body{font:14px/1.55 -apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif;
color:#1d2b24;margin:0;background:#fff}main{max-width:820px;margin:0 auto;padding:40px 36px}
header{border-bottom:3px solid #17603a;padding-bottom:10px;margin-bottom:18px;display:flex;justify-content:space-between;align-items:end}
header b{color:#17603a;letter-spacing:.02em}header span{color:#627269;font-size:12px}
h1{font-size:24px;margin:0 0 4px;letter-spacing:-.02em}h2{font-size:16px;margin:22px 0 8px;color:#17603a;border-bottom:1px solid #d5dfd7;padding-bottom:4px}
p{margin:6px 0}ul{margin:6px 0;padding-left:20px}li{margin:3px 0}em{color:#627269}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:12.5px;font-variant-numeric:tabular-nums}
th,td{border:1px solid #d5dfd7;padding:6px 8px;text-align:left;vertical-align:top}th{background:#eef5ef}
.print{position:fixed;bottom:16px;right:16px;padding:8px 14px;border:1px solid #17603a;background:#17603a;color:#fff;font:inherit;cursor:pointer}
@media print{.print{display:none}main{padding:0}h2{break-after:avoid}table,tr{break-inside:avoid}@page{margin:16mm}}
"""


def _inline(text: str) -> str:
    t = html.escape(text, quote=True)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    return re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", t)


def markdown_to_html(md: str, title: str) -> str:
    out, in_list, table = [], False, []

    def flush_table():
        if not table:
            return
        head, *rows = table
        out.append("<table><thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                   + "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")
        table.clear()

    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not all(set(c) <= {"-", ":"} and c for c in cells):  # skip the |---| separator row
                table.append(cells)
            continue
        flush_table()
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_inline(line[2:])}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if line.startswith("## "):
            out.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line:
            out.append(f"<p>{_inline(line)}</p>")
    flush_table()
    if in_list:
        out.append("</ul>")
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>"
            "<button class=\"print\" onclick=\"window.print()\">Print / Save as PDF</button><main>"
            "<header><b>OPERATION STORM</b><span>Portfolio disaster impact</span></header>" + "".join(out) + "</main></body></html>")
