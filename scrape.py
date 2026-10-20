#!/usr/bin/env python3
"""Run every scraper, merge into events.json. A venue that fails or returns nothing keeps its old data."""
import json, sys, traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from scrapers.venues import REGISTRY

ROOT = Path(__file__).parent
EV = ROOT / "events.json"


def load():
    t = EV.read_text()
    return json.loads(t) if t.lstrip().startswith("[") else [json.loads(l) for l in t.splitlines() if l.strip()]


def main(only=None):
    today = datetime.now(ZoneInfo("America/Chicago")).date()
    events = [e for e in load() if e["date"] >= today.isoformat()]
    fresh, report = {}, []
    for name, (fn, keys) in REGISTRY.items():
        if only and name not in only:
            continue
        try:
            got = fn(today)
            got = [e for e in got if e["date"] >= today.isoformat()]
        except Exception as ex:
            report.append(f"FAIL  {name}: {type(ex).__name__}: {ex}")
            traceback.print_exc(file=sys.stderr)
            continue
        if not got:
            report.append(f"EMPTY {name}: kept old data")
            continue
        fresh[name] = (got, keys)
        report.append(f"ok    {name}: {len(got)} shows")
    for name, (got, keys) in fresh.items():
        events = [e for e in events if e["venue"] not in keys]
    for name, (got, keys) in fresh.items():
        have = {(e["date"], e["venue"], e["headliner"].lower()) for e in events}
        events += [e for e in got if (e["date"], e["venue"], e["headliner"].lower()) not in have]
    events.sort(key=lambda e: (e["date"], e.get("show") or e.get("doors") or "99", e["venue"]))
    EV.write_text("[\n" + ",\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n]\n")
    print("\n".join(report))
    print(f"{len(events)} events written")
    return 0 if fresh else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
