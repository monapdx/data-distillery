"""
Print CORE overlap-by-year counts from core_timeline.csv.

Refactor notes:
- Removed hardcoded path (CLI arg).
- Logic unchanged.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path


def core_overlap_by_year(core_timeline_csv: str):
    years = Counter()

    with open(core_timeline_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            start_year = int(r["start"][:4])
            end_year = int(r["end"][:4])
            for y in range(start_year, end_year + 1):
                years[y] += 1

    print("\n=== CORE OVERLAP BY YEAR ===")
    for y in sorted(years):
        print(f"{y}: {years[y]}")
    return years


def main():
    parser = argparse.ArgumentParser(description="Preview core timeline overlap by year.")
    parser.add_argument("--in", dest="in_csv", default=str(Path("output") / "core_timeline.csv"))
    args = parser.parse_args()
    core_overlap_by_year(args.in_csv)


if __name__ == "__main__":
    main()
