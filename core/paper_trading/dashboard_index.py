"""Dashboard index — scan reports dir, generate index HTML. No network."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass(frozen=True)
class ReportEntry:
    name: str
    path: str
    size_bytes: int
    modified: str


def scan_reports(report_dir: str) -> List[ReportEntry]:
    """Scan a directory for .md and .html reports."""
    entries: List[ReportEntry] = []
    if not os.path.isdir(report_dir):
        return entries
    for fname in sorted(os.listdir(report_dir)):
        if not (fname.endswith(".md") or fname.endswith(".html")):
            continue
        if not fname.startswith("paper_trading"):
            continue
        fpath = os.path.join(report_dir, fname)
        stat = os.stat(fpath)
        entries.append(ReportEntry(
            name=fname,
            path=fpath,
            size_bytes=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        ))
    return entries


def generate_index_html(entries: List[ReportEntry], report_dir: str = "") -> str:
    """Generate a self-contained index HTML listing all reports."""
    rows = ""
    for e in entries:
        size_kb = e.size_bytes / 1024
        ext_icon = "HTML" if e.name.endswith(".html") else "MD"
        rows += (
            f'<tr><td><span class="badge badge-{ext_icon.lower()}">{ext_icon}</span></td>'
            f'<td>{e.name}</td><td>{size_kb:.1f} KB</td><td>{e.modified}</td></tr>\n'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paper Trading Reports Index</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #333; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 10px; }}
  .card {{ background: white; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
  th {{ background: #16213e; color: white; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold; color: white; }}
  .badge-html {{ background: #e67e22; }}
  .badge-md {{ background: #3498db; }}
  .count {{ font-size: 2em; font-weight: bold; color: #1a1a2e; }}
  .footer {{ margin-top: 30px; padding: 15px; background: #1a1a2e; color: #aaa; border-radius: 8px; text-align: center; font-size: 0.85em; }}
</style>
</head>
<body>
<div class="container">
<h1>Paper Trading Reports Index</h1>
<div class="card">
  <p><span class="count">{len(entries)}</span> reports found</p>
</div>
<div class="card">
<table>
  <tr><th>Type</th><th>Report</th><th>Size</th><th>Modified</th></tr>
  {rows}
</table>
</div>
<div class="footer">
  Paper Trading Reports Index | Mode: paper-only | Generated locally
</div>
</div>
</body>
</html>"""


def write_index(report_dir: str, output_path: Optional[str] = None) -> str:
    """Scan report_dir and write index HTML. Returns path written."""
    entries = scan_reports(report_dir)
    if output_path is None:
        output_path = os.path.join(report_dir, "paper_trading_index.html")
    html = generate_index_html(entries, report_dir)
    with open(output_path, "w") as f:
        f.write(html)
    return output_path
