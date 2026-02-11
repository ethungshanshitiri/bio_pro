#!/usr/bin/env python3
"""
Experimental Google Scholar updater.

Important
  Google Scholar has no official public API. This script relies on an unofficial client
  and may fail due to rate limiting or CAPTCHA. Prefer ORCID if possible.

Environment variables
  SCHOLAR_USER_ID  required
  MAX_PUBS         optional, default 200

Output
  data/publications.json
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "publications.json"

def guess_bucket(venue: str) -> str:
    v = (venue or "").lower()
    if any(k in v for k in ["proceedings", "conference", "workshop", "symposium", "nanocom", "icc", "globecom", "wc nc", "wcnc"]):
        return "conferences"
    if any(k in v for k in ["chapter", "book"]):
        return "book_chapters"
    return "journals"

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def parse_year(bib: Dict[str, Any]) -> int:
    y = bib.get("year")
    try:
        return int(y)
    except Exception:
        return 0

def main() -> None:
    user_id = (os.environ.get("SCHOLAR_USER_ID") or "").strip()
    if not user_id:
        raise SystemExit("Missing SCHOLAR_USER_ID")

    max_pubs = int((os.environ.get("MAX_PUBS") or "200").strip())

    try:
        from scholarly import scholarly
    except Exception as e:
        raise SystemExit("Missing dependency scholarly. In GitHub Actions, add: pip install scholarly") from e

    author = scholarly.search_author_id(user_id)
    author = scholarly.fill(author, sections=["publications"])

    pubs = author.get("publications", [])[:max_pubs]

    items: List[Dict[str, Any]] = []
    for p in pubs:
        fp = scholarly.fill(p)
        bib = fp.get("bib", {}) or {}
        title = clean(bib.get("title", ""))
        venue = clean(bib.get("venue", "")) or clean(bib.get("journal", "")) or clean(bib.get("conference", ""))
        year = clean(str(bib.get("year", "")))
        authors = clean(bib.get("author", ""))

        bucket = guess_bucket(venue)

        # DOI is rarely present in Scholar bib, keep link if present
        doi = None
        m = re.search(r"\b10\.\d{4,9}/[^\s\)\]\;]+", fp.get("pub_url", "") or "")
        if m:
            doi = m.group(0).rstrip(".,;)")
        url = f"https://doi.org/{doi}" if doi else (fp.get("pub_url") or None)

        citation = f"{authors}, \"{title}\", {venue}, {year}."
        items.append({
            "bucket": bucket,
            "year": parse_year(bib),
            "citation": citation,
            "doi": doi,
            "url": url,
        })

    out = {
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": f"google_scholar:{user_id}",
        "journals": [],
        "conferences": [],
        "book_chapters": [],
    }

    grouped = {"journals": [], "conferences": [], "book_chapters": []}
    for it in items:
        grouped[it["bucket"]].append(it)

    for bucket, lst in grouped.items():
        lst.sort(key=lambda x: x["year"])
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
        numbered.sort(key=lambda x: x["number"], reverse=True)
        out[bucket] = numbered

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
