"""Mock replay evidence browser."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class EvidenceFilter:
    filter_id: str
    category: str
    keyword: str
    match_count: int
    def to_dict(self) -> dict:
        return {"filter_id": self.filter_id, "category": self.category, "keyword": self.keyword, "match_count": self.match_count}


@dataclass(frozen=True)
class EvidenceBrowserResult:
    browse_id: str
    created_at: str
    total_items: int
    filters_applied: tuple[EvidenceFilter, ...]
    matched_items: tuple[dict, ...]
    def to_dict(self) -> dict:
        return {"browse_id": self.browse_id, "created_at": self.created_at, "total_items": self.total_items, "filters_applied": [f.to_dict() for f in self.filters_applied], "matched_items": list(self.matched_items)}


def browse_evidence(bundle: dict, filters: list[dict] | None = None) -> EvidenceBrowserResult:
    items = bundle.get("items", [])
    applied: list[EvidenceFilter] = []
    matched = list(items)

    if filters:
        for f in filters:
            cat = f.get("category", "")
            kw = f.get("keyword", "")
            if cat:
                matched = [m for m in matched if m.get("category") == cat]
            if kw:
                matched = [m for m in matched if kw.lower() in str(m.get("content", "")).lower() or kw.lower() in str(m.get("title", "")).lower()]
            applied.append(EvidenceFilter(
                filter_id=f"FLT_{uuid.uuid4().hex[:8]}",
                category=cat,
                keyword=kw,
                match_count=len(matched),
            ))

    return EvidenceBrowserResult(
        browse_id=f"BRW_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        total_items=len(items),
        filters_applied=tuple(applied),
        matched_items=tuple(matched),
    )


def search_evidence(bundle: dict, query: str) -> list[dict]:
    items = bundle.get("items", [])
    q = query.lower()
    return [i for i in items if q in str(i.get("content", "")).lower() or q in str(i.get("title", "")).lower()]


def categorize_evidence(bundle: dict) -> dict[str, list[dict]]:
    items = bundle.get("items", [])
    cats: dict[str, list[dict]] = {}
    for item in items:
        cat = item.get("category", "uncategorized")
        cats.setdefault(cat, []).append(item)
    return cats


def write_result(result: EvidenceBrowserResult, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


def render_report(result: EvidenceBrowserResult) -> str:
    lines = ["# Mock Replay Evidence Browser", "",
        f"**browse_id={result.browse_id}**",
        "**MOCK_EVIDENCE_ONLY**",
        "**REAL_TESTNET_SUBMIT_NOT_ALLOWED**", "",
        f"Total items: {result.total_items}",
        f"Filters applied: {len(result.filters_applied)}",
        f"Matched items: {len(result.matched_items)}", ""]
    if result.filters_applied:
        lines.append("## Filters Applied")
        lines.append("")
        for f in result.filters_applied:
            lines.append(f"- category={f.category}, keyword={f.keyword}, matches={f.match_count}")
        lines.append("")
    lines.extend(["## Conclusion", "", "MOCK_REPLAY_EVIDENCE_BROWSER_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
