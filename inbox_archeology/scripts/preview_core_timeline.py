"""Preview CORE overlap by year from core_timeline.csv.

Refactor notes:
- Removed hardcoded paths.
- Added CLI args (--in).
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

def preview_core_overlap(in_path: str) -> None:
    path = Path(in_path)
    years = Counter()

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            start_year = int(r["start"][:4])
            end_year = int(r["end"][:4])
            for y in range(start_year, end_year + 1):
                years[y] += 1

    print("\n=== CORE OVERLAP BY YEAR ===")
    for y in sorted(years):
        print(f"{y}: {years[y]}")

def main():
    p = argparse.ArgumentParser(description="Preview core overlap by year.")
    p.add_argument("--in", dest="inp", default=str(Path("output")/"core_timeline.csv"))
    args = p.parse_args()
    preview_core_overlap(args.inp)

if __name__ == "__main__":
    main()
