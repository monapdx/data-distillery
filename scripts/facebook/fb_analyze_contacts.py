import os
import re
import csv
from datetime import datetime
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

INDEX_FILE = "messages.htm"
MESSAGES_DIR = "messages"

EXCLUDE_NAME = "Facebook User"

def is_group_title(title: str) -> bool:
    """
    Heuristic: group threads in messages.htm typically show multiple names separated by commas.
    Facebook full names rarely contain commas, so this is safe for exports like yours.
    """
    return "," in title

def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def parse_index(index_path: str):
    """
    Returns list of dicts: {href, title}
    """
    with open(index_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    rows = []
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        if href.startswith("messages/") and href.endswith(".html"):
            title = normalize_ws(a.get_text(" ", strip=True))
            rows.append({"href": href, "title": title})
    return rows

def parse_timestamp(meta_text: str):
    """
    Meta strings look like:
      'Wednesday, October 7, 2015 at 11:52pm PST'
    We parse using dateutil, ignoring timezone abbreviations if needed.
    """
    t = normalize_ws(meta_text)
    # Some exports include PST/PDT; dateutil sometimes parses, sometimes not.
    # Strip trailing TZ abbrev if it breaks parsing.
    try:
        return dateparser.parse(t, fuzzy=True)
    except Exception:
        t2 = re.sub(r"\b(PST|PDT|EST|EDT|CST|CDT|MST|MDT)\b", "", t).strip()
        try:
            return dateparser.parse(t2, fuzzy=True)
        except Exception:
            return None

def conversation_stats(thread_path: str):
    """
    Fast-ish scan:
    - counts number of header blocks div.message
    - finds min/max timestamps from span.meta
    """
    with open(thread_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    metas = soup.select("span.meta")
    times = []
    for m in metas:
        dt = parse_timestamp(m.get_text(" ", strip=True))
        if dt:
            times.append(dt)

    msg_count = len(soup.select("div.message"))
    if not times:
        return msg_count, None, None
    return msg_count, min(times), max(times)

def main():
    base = os.getcwd()
    index_path = os.path.join(base, INDEX_FILE)
    messages_dir = os.path.join(base, MESSAGES_DIR)

    if not os.path.isfile(index_path):
        raise SystemExit(f"Missing {INDEX_FILE} in {base}")
    if not os.path.isdir(messages_dir):
        raise SystemExit(f"Missing folder {MESSAGES_DIR}/ in {base}")

    threads = parse_index(index_path)

    one_to_one = []
    for row in threads:
        title = row["title"]
        href = row["href"]
        if not title or title == EXCLUDE_NAME:
            continue
        if is_group_title(title):
            continue

        thread_path = os.path.join(base, href.replace("/", os.sep))
        if not os.path.isfile(thread_path):
            continue

        msg_count, first_dt, last_dt = conversation_stats(thread_path)
        if title == EXCLUDE_NAME:
            continue

        span_days = None
        if first_dt and last_dt:
            span_days = (last_dt - first_dt).days

        one_to_one.append({
            "contact": title,
            "file": href,
            "messages": msg_count,
            "first": first_dt.isoformat(sep=" ") if first_dt else "",
            "last": last_dt.isoformat(sep=" ") if last_dt else "",
            "span_days": span_days if span_days is not None else -1
        })

    # Top by message volume
    top_volume = sorted(one_to_one, key=lambda x: x["messages"], reverse=True)[:15]

    # Top by longest span (requires timestamps)
    top_span = sorted(one_to_one, key=lambda x: x["span_days"], reverse=True)[:15]

    # Print results
    print("\nTOP 15 CONTACTS BY MESSAGE COUNT (1:1 only)")
    for i, r in enumerate(top_volume, 1):
        print(f"{i:>2}. {r['contact']} — {r['messages']} msgs — {r['file']}")

    print("\nTOP 15 CONTACTS BY LONGEST TIMESPAN (1:1 only)")
    for i, r in enumerate(top_span, 1):
        if r["span_days"] < 0:
            continue
        print(f"{i:>2}. {r['contact']} — {r['span_days']} days — {r['first']} → {r['last']} — {r['file']}")

    # Also write a CSV you can reuse in Streamlit
    out_csv = os.path.join(base, "fb_thread_stats.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["contact", "file", "messages", "first", "last", "span_days"])
        w.writeheader()
        w.writerows(one_to_one)

    print(f"\nWrote: {out_csv}")

if __name__ == "__main__":
    main()
