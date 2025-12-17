"""Plot CORE timeline as a horizontal bar chart.

Refactor notes:
- Removed hardcoded paths.
- Added CLI args (--in, --save).
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt

def plot_core_timeline(in_path: str, save_path: str | None = None) -> None:
    path = Path(in_path)
    rows = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "email": r["email"],
                "start": datetime.fromisoformat(r["start"]),
                "end": datetime.fromisoformat(r["end"]),
                "total": int(r["total_messages"]),
            })

    rows.sort(key=lambda r: r["start"])

    y_positions = range(len(rows))
    starts = [r["start"] for r in rows]
    durations = [(r["end"] - r["start"]).days for r in rows]

    plt.figure(figsize=(12, max(6, len(rows) * 0.25)))
    plt.barh(y_positions, durations, left=starts)
    plt.xlabel("Year")
    plt.ylabel("CORE relationships (ordered by start date)")
    plt.title("CORE Relationship Timeline")
    plt.yticks([])
    plt.tight_layout()

    if save_path:
        sp = Path(save_path)
        sp.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(sp, dpi=200)
        print(f"Saved: {sp}")
    else:
        plt.show()

def main():
    p = argparse.ArgumentParser(description="Plot core timeline.")
    p.add_argument("--in", dest="inp", default=str(Path("output")/"core_timeline.csv"))
    p.add_argument("--save", default="", help="Optional path to save PNG instead of showing it.")
    args = p.parse_args()
    plot_core_timeline(args.inp, args.save if args.save.strip() else None)

if __name__ == "__main__":
    main()
