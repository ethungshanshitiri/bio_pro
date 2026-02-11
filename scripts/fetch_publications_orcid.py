#!/usr/bin/env python3
"""
Update data/publications.json from ORCID works.

Supports both unauthenticated and token-based requests.
If ORCID returns 401, set ORCID_TOKEN as a GitHub secret and the workflow will use it.

Environment variables
  ORCID_ID     required
  ORCID_TOKEN  optional

Output
  data/publications.json
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "publications.json"

ORCID_ID = (os.environ.get("ORCID_ID") or "").strip()
ORCID_TOKEN = (os.environ.get("ORCID_TOKEN") or "").strip()

USER_AGENT = "cv-site-publications-updater/1.0 (+https://github.com/)"

HEADERS_BASE = {
    "Accept": "application/json",
    "User-Agent": USER_AGENT,
}

def _headers() -> Dict[str, str]:
    h = dict(HEADERS_BASE)
    if ORCID_TOKEN:
        h["Authorization"] = f"Bearer {ORCID_TOKEN}"
    return h

def _get(url: str) -> Dict[str, Any]:
    resp = requests.get(url, headers=_headers(), timeout=30)
    if resp.status_code == 401 and not ORCID_TOKEN:
        raise RuntimeError("ORCID returned 401. Set ORCID_TOKEN as a secret to enable authenticated reads.")
    resp.raise_for_status()
    return resp.json()

def _safe_get(d: Dict[str, Any], path: List[str], default=None):
    cur: Any = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

def _date_tuple(work: Dict[str, Any]) -> Tuple[int, int, int]:
    y = _safe_get(work, ["publication-date", "year", "value"], None)
    m = _safe_get(work, ["publication-date", "month", "value"], None)
    d = _safe_get(work, ["publication-date", "day", "value"], None)
    try:
        yi = int(y) if y else 0
        mi = int(m) if m else 0
        di = int(d) if d else 0
    except Exception:
        return (0, 0, 0)
    return (yi, mi, di)

def _extract_doi(work: Dict[str, Any]) -> Optional[str]:
    ext_ids = _safe_get(work, ["external-ids", "external-id"], []) or []
    for eid in ext_ids:
        t = (eid.get("external-id-type") or "").lower()
        if t == "doi":
            v = (eid.get("external-id-value") or "").strip()
            v = v.rstrip(".,;)")
            if v:
                return v
    return None

def _type_to_bucket(t: str) -> str:
    t = (t or "").lower().strip()
    if t in {"journal-article", "journal article", "journal_article"}:
        return "journals"
    if t in {"conference-paper", "conference paper", "conference_paper"}:
        return "conferences"
    if t in {"book-chapter", "book chapter", "book_chapter"}:
        return "book_chapters"
    # conservative fallback
    return "journals"

def _contributors_to_authors(work_detail: Dict[str, Any]) -> List[str]:
    contribs = _safe_get(work_detail, ["contributors", "contributor"], []) or []
    authors: List[str] = []
    for c in contribs:
        name = _safe_get(c, ["credit-name", "value"], "") or ""
        name = re.sub(r"\s+", " ", name).strip()
        if name:
            authors.append(name)
    return authors

def _format_ieee_like(authors: List[str], title: str, venue: str, year: str, doi: Optional[str]) -> str:
    # Keep it simple and stable.
    a = ", ".join(authors) if authors else "Unknown authors"
    parts = [f"{a}, \"{title}\""]
    if venue:
        parts.append(venue)
    if year:
        parts.append(year)
    if doi:
        parts.append(f"doi {doi}")
    return ", ".join(parts) + "."

def main() -> None:
    if not ORCID_ID:
        raise SystemExit("Missing ORCID_ID")

    works_url = f"https://pub.orcid.org/v3.0/{ORCID_ID}/works"
    works = _get(works_url)

    groups = works.get("group", []) or []
    summaries: List[Dict[str, Any]] = []
    for g in groups:
        ws = g.get("work-summary", []) or []
        for w in ws:
            summaries.append(w)

    # De-duplicate by put-code, keep the first occurrence.
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for w in summaries:
        pc = w.get("put-code")
        if pc in seen:
            continue
        seen.add(pc)
        uniq.append(w)

    # Fetch details for better metadata (contributors, journal title).
    detailed: List[Dict[str, Any]] = []
    for w in uniq:
        pc = w.get("put-code")
        if pc is None:
            continue
        detail_url = f"https://pub.orcid.org/v3.0/{ORCID_ID}/work/{pc}"
        try:
            wd = _get(detail_url)
        except Exception:
            wd = {}
        # Attach summary fields if detail is missing
        wd["_summary"] = w
        detailed.append(wd)

    items: List[Dict[str, Any]] = []
    for wd in detailed:
        wsum = wd.get("_summary", {}) or {}
        title = _safe_get(wd, ["title", "title", "value"], None) or _safe_get(wsum, ["title", "title", "value"], "") or ""
        title = re.sub(r"\s+", " ", title).strip()

        wtype = _safe_get(wd, ["type"], None) or _safe_get(wsum, ["type"], "") or ""
        bucket = _type_to_bucket(wtype)

        venue = _safe_get(wd, ["journal-title", "value"], None) or _safe_get(wsum, ["journal-title", "value"], "") or ""
        venue = re.sub(r"\s+", " ", venue).strip()

        doi = _extract_doi(wd) or _extract_doi(wsum)
        url = f"https://doi.org/{doi}" if doi else None

        y = _safe_get(wd, ["publication-date", "year", "value"], None) or _safe_get(wsum, ["publication-date", "year", "value"], "") or ""
        y = str(y).strip() if y else ""

        authors = _contributors_to_authors(wd)
        citation = _format_ieee_like(authors, title, venue, y, doi)

        items.append({
            "bucket": bucket,
            "date": _date_tuple(wd) if wd else _date_tuple(wsum),
            "citation": citation,
            "doi": doi,
            "url": url,
        })

    out = {
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": f"orcid:{ORCID_ID}",
        "journals": [],
        "conferences": [],
        "book_chapters": [],
    }

    # Group and sort by date ascending for numbering
    grouped = {"journals": [], "conferences": [], "book_chapters": []}
    for it in items:
        grouped[it["bucket"]].append(it)

    for bucket, lst in grouped.items():
        lst.sort(key=lambda x: x["date"])
        # assign numbers 1..N in chronological order, latest gets N
        numbered = []
        for i, it in enumerate(lst, start=1):
            prefix = "j" if bucket == "journals" else ("c" if bucket == "conferences" else "b")
            label = f"{prefix}{i}"
            numbered.append({
                "id": label,
                "label": label,
                "number": i,
                "citation": it["citation"],
                "doi": it["doi"],
                "url": it["url"],
            })
        # display newest first
        numbered.sort(key=lambda x: x["number"], reverse=True)
        out[bucket] = numbered

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
