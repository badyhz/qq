"""T1841 - Frozen Backlog HTML Dashboard Renderer.

Pure functions that produce HTML strings. No I/O. No timestamps.
No external CDN, no network resources. Inline CSS only.
No JavaScript (or minimal inline static deterministic JS only).
"""
from __future__ import annotations

import html as _html

from core.frozen_backlog_report_record import FrozenBacklogReportRecord
from core.frozen_backlog_report_summary import FrozenBacklogReportSummary


def _esc(text: str) -> str:
    """HTML-escape a string."""
    return _html.escape(text, quote=True)


def render_hold_banner_html() -> str:
    """Render the HOLD warning banner."""
    return (
        '<div class="hold-banner">'
        '<span class="hold-icon">&#9888;</span> '
        '<strong>RELEASE HOLD</strong> &mdash; '
        'All frozen backlog files are under HOLD. '
        'No live trading, no submissions, no exchange calls permitted.'
        '</div>'
    )


def render_summary_cards_html(summary: FrozenBacklogReportSummary) -> str:
    """Render summary cards section."""
    cards = [
        ("Total Files", str(summary.total_files), "card-total"),
        ("High Risk", str(summary.high_risk_count), "card-high"),
        ("Medium Risk", str(summary.medium_risk_count), "card-medium"),
        ("Release Hold", _esc(summary.release_hold), "card-hold"),
    ]
    parts: list[str] = ['<div class="summary-cards">']
    for label, value, css_class in cards:
        parts.append(
            f'<div class="card {css_class}">'
            f'<div class="card-value">{value}</div>'
            f'<div class="card-label">{_esc(label)}</div>'
            f'</div>'
        )
    parts.append('</div>')
    return "\n".join(parts)


def render_risk_distribution_html(summary: FrozenBacklogReportSummary) -> str:
    """Render risk distribution visualization with colored bars."""
    total = summary.total_files
    if total == 0:
        return '<div class="risk-distribution"><p>No files.</p></div>'

    high_pct = (summary.high_risk_count / total) * 100
    med_pct = (summary.medium_risk_count / total) * 100

    return (
        '<div class="risk-distribution">'
        '<h3>Risk Distribution</h3>'
        '<div class="bar-container">'
        f'<div class="bar bar-high" style="width: {high_pct:.1f}%;">'
        f'HIGH ({summary.high_risk_count})</div>'
        f'<div class="bar bar-medium" style="width: {med_pct:.1f}%;">'
        f'MEDIUM ({summary.medium_risk_count})</div>'
        '</div>'
        '</div>'
    )


def render_file_table_html(records: tuple[FrozenBacklogReportRecord, ...]) -> str:
    """Render table of all files with key columns."""
    header = (
        '<thead><tr>'
        '<th>#</th>'
        '<th>File Path</th>'
        '<th>Risk Class</th>'
        '<th>Category</th>'
        '<th>Allowed Actions</th>'
        '<th>Forbidden Actions</th>'
        '<th>Readiness</th>'
        '<th>Unlock Rec.</th>'
        '</tr></thead>'
    )
    rows: list[str] = []
    for idx, rec in enumerate(records):
        risk_class = _esc(rec.risk_class)
        risk_css = "risk-high" if rec.risk_class == "HIGH" else "risk-medium"
        allowed = ", ".join(_esc(a) for a in rec.allowed_actions)
        forbidden = ", ".join(_esc(a) for a in rec.forbidden_actions)
        rows.append(
            '<tr>'
            f'<td>{idx + 1}</td>'
            f'<td class="file-path">{_esc(rec.file_path)}</td>'
            f'<td class="{risk_css}">{risk_class}</td>'
            f'<td>{_esc(rec.category)}</td>'
            f'<td class="actions-allowed">{allowed}</td>'
            f'<td class="actions-forbidden">{forbidden}</td>'
            f'<td>{rec.readiness_score:.1f}</td>'
            f'<td>{_esc(rec.unlock_recommendation)}</td>'
            '</tr>'
        )
    tbody = "<tbody>" + "\n".join(rows) + "</tbody>"
    return (
        '<div class="file-table">'
        '<h3>Frozen Backlog Files</h3>'
        f'<table>{header}{tbody}</table>'
        '</div>'
    )


_CSS = """\
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #333; }
.hold-banner { background: #d32f2f; color: #fff; padding: 16px 24px; border-radius: 6px; margin-bottom: 24px; font-size: 18px; }
.hold-icon { font-size: 22px; }
.summary-cards { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
.card { background: #fff; border-radius: 6px; padding: 20px 24px; min-width: 140px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); text-align: center; }
.card-value { font-size: 32px; font-weight: 700; }
.card-label { font-size: 13px; color: #666; margin-top: 4px; }
.card-high .card-value { color: #d32f2f; }
.card-medium .card-value { color: #f57c00; }
.card-hold .card-value { color: #d32f2f; }
.card-total .card-value { color: #1976d2; }
.risk-distribution { margin-bottom: 24px; }
.risk-distribution h3 { margin-bottom: 8px; }
.bar-container { display: flex; height: 32px; border-radius: 4px; overflow: hidden; background: #e0e0e0; }
.bar { display: flex; align-items: center; justify-content: center; color: #fff; font-size: 13px; font-weight: 600; white-space: nowrap; }
.bar-high { background: #d32f2f; }
.bar-medium { background: #f57c00; }
.file-table { margin-bottom: 24px; }
.file-table h3 { margin-bottom: 8px; }
table { width: 100%; border-collapse: collapse; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #e0e0e0; font-size: 13px; }
th { background: #1976d2; color: #fff; font-weight: 600; }
tr:hover { background: #f5f5f5; }
.file-path { font-family: 'SF Mono', Monaco, Consolas, monospace; font-size: 12px; }
.risk-high { color: #d32f2f; font-weight: 700; }
.risk-medium { color: #f57c00; font-weight: 700; }
.actions-allowed { color: #388e3c; font-size: 12px; }
.actions-forbidden { color: #d32f2f; font-size: 12px; }
.dashboard-footer { margin-top: 32px; padding-top: 16px; border-top: 1px solid #e0e0e0; color: #999; font-size: 12px; }
.safety-flags { margin-bottom: 24px; background: #fff; padding: 16px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
.safety-flags h3 { margin-top: 0; }
.flag-true { color: #388e3c; font-weight: 700; }
.flag-label { display: inline-block; min-width: 200px; }
"""


def render_dashboard_html(
    summary: FrozenBacklogReportSummary,
    records: tuple[FrozenBacklogReportRecord, ...],
) -> str:
    """Render full HTML dashboard page."""
    safety_flags = [
        ("No Live", summary.no_live),
        ("No Submit", summary.no_submit),
        ("No Exchange", summary.no_exchange),
        ("No Runtime Integration", summary.no_runtime_integration),
        ("No Planner Integration", summary.no_planner_integration),
    ]
    flags_html_parts: list[str] = [
        '<div class="safety-flags">',
        '<h3>Safety Constraints</h3>',
    ]
    for label, value in safety_flags:
        flag_text = "TRUE" if value else "FALSE"
        css = "flag-true" if value else "flag-false"
        flags_html_parts.append(
            f'<div><span class="flag-label">{_esc(label)}:</span> '
            f'<span class="{css}">{flag_text}</span></div>'
        )
    flags_html_parts.append('</div>')
    flags_html = "\n".join(flags_html_parts)

    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>Frozen Backlog Review Dashboard</title>\n'
        f'<style>{_CSS}</style>\n'
        '</head>\n<body>\n'
        '<h1>Frozen Backlog Review Dashboard</h1>\n'
        f'{render_hold_banner_html()}\n'
        f'{render_summary_cards_html(summary)}\n'
        f'{render_risk_distribution_html(summary)}\n'
        f'{flags_html}\n'
        f'{render_file_table_html(records)}\n'
        '<div class="dashboard-footer">'
        'Frozen Backlog Review Platform v1 &mdash; All data is static. '
        'release_hold=HOLD enforced.'
        '</div>\n'
        '</body>\n</html>'
    )
