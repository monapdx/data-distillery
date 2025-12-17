"""Build a CORE-only timeline CSV from relationships_clean.csv.

Refactor notes:
- Removed hardcoded paths.
- Added CLI args (--in, --out, --core-min).
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path

def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def build_core_timeline(in_path: str, out_path: str, core_min: int = 100) -> int:
    in_path = Path(in_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with in_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            total = int(r["total_messages"])
            if total < core_min:
                continue
            start = parse_dt(r.get("first_contact"))
            end = parse_dt(r.get("last_contact"))
            if not start or not end:
                continue
            duration_days = (end - start).days
            duration_years = round(duration_days / 365.25, 2)
            rows.append({
                "email": r["email"],
                "start": start.date().isoformat(),
                "end": end.date().isoformat(),
                "duration_days": duration_days,
                "duration_years": duration_years,
                "total_messages": total,
            })

    rows.sort(key=lambda r: r["start"])

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["email","start","end","duration_days","duration_years","total_messages"],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"CORE timeline written to {out_path}")
    print(f"CORE relationships: {len(rows)}")
    return len(rows)

def main():
    p = argparse.ArgumentParser(description="Build core_timeline.csv from relationships_clean.csv.")
    p.add_argument("--in", dest="inp", default=str(Path('output')/'relationships_clean.csv'))
    p.add_argument("--out", default=str(Path('output')/'core_timeline.csv'))
    p.add_argument("--core-min", type=int, default=100)
    args = p.parse_args()
    build_core_timeline(args.inp, args.out, args.core_min)

if __name__ == "__main__":
    main()
