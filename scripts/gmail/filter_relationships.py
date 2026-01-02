"""
Filter relationships_raw.csv into relationships_filtered.csv.

Refactor notes:
- Removed hardcoded paths (CLI args).
- Logic unchanged.
"""

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path


def parse_dt(s: str):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s)
    except Exception:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def filter_relationships_csv(
    in_path: str,
    out_path: str,
    min_messages: int = 5,
    min_active_days: int = 30,
):
    kept = []
    dropped = 0
    total = 0

    bins = {"1": 0, "2-4": 0, "5-9": 0, "10-24": 0, "25-99": 0, "100+": 0}

    def bin_count(n: int) -> str:
        if n == 1: return "1"
        if 2 <= n <= 4: return "2-4"
        if 5 <= n <= 9: return "5-9"
        if 10 <= n <= 24: return "10-24"
        if 25 <= n <= 99: return "25-99"
        return "100+"

    with open(in_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            n = int(row["total_messages"])
            bins[bin_count(n)] += 1

            first = parse_dt(row.get("first_contact", ""))
            last = parse_dt(row.get("last_contact", ""))
            active_days = None
            if first and last:
                active_days = (last - first).days

            keep = (n >= min_messages) or (active_days is not None and active_days >= min_active_days)

            if keep:
                row["active_days"] = str(active_days) if active_days is not None else ""
                kept.append(row)
            else:
                dropped += 1

    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)

    with outp.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "email",
            "total_messages",
            "sent_by_me",
            "received_by_me",
            "first_contact",
            "last_contact",
            "active_days",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        kept.sort(key=lambda r: int(r["total_messages"]), reverse=True)
        for r in kept:
            writer.writerow(r)

    print("\n=== FILTER RESULTS (Balanced) ===")
    print(f"Rule: keep if total_messages >= {min_messages} OR active_days >= {min_active_days}")
    print(f"Total addresses: {total:,}")
    print(f"Kept: {len(kept):,}")
    print(f"Dropped: {dropped:,}")

    print("\nMessage-count distribution (all addresses):")
    for k in ["1", "2-4", "5-9", "10-24", "25-99", "100+"]:
        print(f"  {k:>5}: {bins[k]:,}")

    print(f"\nWrote: {outp}\n")
    return str(outp)


def main():
    parser = argparse.ArgumentParser(description="Filter relationships_raw.csv -> relationships_filtered.csv")
    parser.add_argument("--in", dest="in_csv", default=str(Path("output") / "relationships_raw.csv"))
    parser.add_argument("--out", default=str(Path("output") / "relationships_filtered.csv"))
    parser.add_argument("--min-messages", type=int, default=5)
    parser.add_argument("--min-active-days", type=int, default=30)
    args = parser.parse_args()
    filter_relationships_csv(args.in_csv, args.out, args.min_messages, args.min_active_days)


if __name__ == "__main__":
    main()
