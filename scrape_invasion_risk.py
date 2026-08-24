#!/usr/bin/env python3
"""
Daily archiver for the INRB/UMIE invasion-risk forecast (spatial-risk tab).

Source: https://inrb-umie.github.io/BDBV2026-Epidemic_Dashboard/spatial-risk.html

The page embeds its entire data payload inline as
    <script id="payload" type="application/json">{...}</script>
(see INRB-UMIE/BDBV2026-Epidemic_Dashboard, Scripts/common/chrome.py:render_page).
This script fetches that page, pulls out payload["invasion_risk"], and writes
an immutable, timestamped snapshot only when the forecast has actually
changed since the last run (detected via a content hash of the zones dict).

IMPORTANT — do not "shortcut" this by reading the data repo instead:
INRB-UMIE/BDBV2026-Epidemic_Dashboard/Data/invasion_risk_model_estimates.csv
looks like a live source but is a stale local-dev fallback, only used when
the private BDBV2026-Processed_Sensitive_Data repo isn't checked out. Verified
2026-08-23: that CSV was on cutoff_date 2026-07-20 (method Bayes-M8-full)
while the deployed page was on cutoff_date 2026-08-21 (method Bayes-M17-med).
Always scrape the rendered page, never the public data repo's CSV.

Each run either:
  - writes a new JSON snapshot to snapshots/invasion_risk/<cutoff_date>_<hash>.json
    and appends a row to snapshots/invasion_risk_index.csv, or
  - appends an "unchanged" row to the index only (no new snapshot file), or
  - exits non-zero (and writes nothing) if the fetch or parse fails, so a
    missed day is visible in the workflow run history rather than silently
    recorded as "unchanged".

cutoff_date is the model's training-data cutoff (the scientifically
meaningful "as-of" date for the forecast). retrieved_at is wall-clock time of
this scrape. Both are kept — they answer different questions: whether the
forecast changed, versus whether we're polling often enough to catch it.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = "https://inrb-umie.github.io/BDBV2026-Epidemic_Dashboard/spatial-risk.html"
PAYLOAD_RE = re.compile(
    r'<script id="payload" type="application/json">(.*?)</script>', re.S
)
FETCH_TIMEOUT_S = 120

SNAPSHOT_DIR = Path("snapshots/invasion_risk")
INDEX_PATH = Path("snapshots/invasion_risk_index.csv")
INDEX_FIELDS = [
    "retrieved_at",
    "cutoff_date",
    "forecast_start_date",
    "forecast_end_date",
    "method",
    "content_hash",
    "changed",
    "dashboard_built_at",
]


def fetch_payload(url: str = SOURCE_URL) -> dict:
    req = Request(url, headers={"User-Agent": "outbreak-spatial-audit/0.1 (research use)"})
    with urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
        html = resp.read().decode("utf-8")
    match = PAYLOAD_RE.search(html)
    if not match:
        raise RuntimeError(
            'Could not find <script id="payload"> in the fetched page. '
            "The dashboard's HTML structure may have changed \u2014 inspect "
            "the page manually before assuming it's just down."
        )
    return json.loads(match.group(1))


def last_recorded_hash() -> str | None:
    if not INDEX_PATH.exists():
        return None
    with INDEX_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-1]["content_hash"] if rows else None


def append_index_row(row: dict) -> None:
    is_new = not INDEX_PATH.exists()
    with INDEX_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INDEX_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def main() -> int:
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    try:
        payload = fetch_payload()
    except Exception as exc:  # noqa: BLE001 - want any failure surfaced, not swallowed
        print(f"FETCH FAILED at {retrieved_at}: {exc}", file=sys.stderr)
        return 1

    invasion_risk = payload.get("invasion_risk")
    if not invasion_risk or not invasion_risk.get("zones"):
        print(f"FETCH OK but invasion_risk missing/empty at {retrieved_at}", file=sys.stderr)
        return 1

    cutoff_date = invasion_risk.get("cutoff_date", "unknown")
    method = invasion_risk.get("method", "unknown")
    content_hash = hashlib.sha256(
        json.dumps(invasion_risk["zones"], sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]

    changed = content_hash != last_recorded_hash()

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    if changed:
        snapshot_path = SNAPSHOT_DIR / f"{cutoff_date}_{content_hash}.json"
        snapshot = {
            "retrieved_at": retrieved_at,
            "source_url": SOURCE_URL,
            "dashboard_built_at": payload.get("dashboard_built_at"),
            "cutoff_date": cutoff_date,
            "forecast_start_date": invasion_risk.get("forecast_start_date"),
            "forecast_end_date": invasion_risk.get("forecast_end_date"),
            "horizon": invasion_risk.get("horizon"),
            "horizon_window": invasion_risk.get("horizon_window"),
            "method": method,
            "content_hash": content_hash,
            "zones": invasion_risk["zones"],
        }
        snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        print(f"NEW SNAPSHOT: {snapshot_path} (cutoff_date={cutoff_date}, method={method})")
    else:
        print(f"No change since last snapshot (hash={content_hash}); logging check only.")

    append_index_row(
        {
            "retrieved_at": retrieved_at,
            "cutoff_date": cutoff_date,
            "forecast_start_date": invasion_risk.get("forecast_start_date"),
            "forecast_end_date": invasion_risk.get("forecast_end_date"),
            "method": method,
            "content_hash": content_hash,
            "changed": "1" if changed else "0",
            "dashboard_built_at": payload.get("dashboard_built_at"),
        }
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
