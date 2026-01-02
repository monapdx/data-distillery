import json
import csv
from datetime import datetime
from collections import defaultdict
from pathlib import Path

INPUT_FILE = "MyActivity.json"
CSV_OUTPUT = "searches_by_month.csv"
MONTHLY_JSON_DIR = Path("searches_by_month")

def load_activity(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    data = load_activity(INPUT_FILE)

    # For writing a flat CSV
    csv_rows = []

    # For saving per-month JSON (optional)
    MONTHLY_JSON_DIR.mkdir(exist_ok=True)
    by_month = defaultdict(list)

    for item in data:
        # Only keep Search entries (your file has "header": "Search")
        if item.get("header") != "Search":
            continue

        time_str = item.get("time")
        if not time_str:
            continue

        # Example: "2025-01-05T07:16:52.067Z"
        # Replace Z with +00:00 so datetime.fromisoformat is happy
        time_clean = time_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(time_clean)

        year_month = dt.strftime("%Y-%m")          # e.g. "2025-01"
        date_str = dt.date().isoformat()           # "2025-01-05"
        time_of_day = dt.time().isoformat(timespec="seconds")

        title = item.get("title", "")
        url = item.get("titleUrl", "")

        # Add a row for the CSV
        csv_rows.append([year_month, date_str, time_of_day, title, url])

        # Also keep the original item, but add year_month for convenience
        item_with_month = dict(item)
        item_with_month["year_month"] = year_month
        by_month[year_month].append(item_with_month)

    # Write CSV with a year_month column so you can filter in Excel/Sheets
    with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["year_month", "date", "time", "title", "url"])
        writer.writerows(csv_rows)

    # Write one JSON file per month: searches_by_month/2025-01.json, etc.
    for ym, items in by_month.items():
        out_path = MONTHLY_JSON_DIR / f"{ym}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(csv_rows)} search entries to {CSV_OUTPUT}")
    print(f"Monthly JSON files saved in {MONTHLY_JSON_DIR.resolve()}")

if __name__ == "__main__":
    main()
