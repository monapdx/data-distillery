"""Build a per-person relationship table from inbox_metadata.csv.

Refactor notes:
- Removed hardcoded paths.
- Added CLI args (--in, --out).
"""

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---- DEFAULT CONFIG ----
DEFAULT_SELF_ADDRESSES = [
    "",
    "",
]

DEFAULT_AUTOMATED_DOMAINS = [
    "facebookmail.com",
    "google.com",
    "googlemail.com",
    "craigslist.org",
    "nextdoor.com",
    "poshmark.com",
]

DEFAULT_AUTOMATED_PREFIXES = [
    "no-reply@",
    "noreply@",
    "notifications@",
    "support@",
    "help@",
]

def norm_email(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    if "<" in s and ">" in s:
        s = s.split("<")[-1].split(">")[0]
    return s.lower()

def is_automated(email: str, self_addrs: set[str], prefixes: tuple[str, ...], domains: tuple[str, ...]) -> bool:
    if not email:
        return True
    if email in self_addrs:
        return True
    for p in prefixes:
        if email.startswith(p):
            return True
    for d in domains:
        if email.endswith("@" + d):
            return True
    return False

def parse_date(s: str):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s)
    except Exception:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    else:
        d = d.astimezone(timezone.utc)
    # clamp insane future dates
    if d.year > datetime.now().year + 1:
        return None
    return d

def extract_relationships(
    inbox_metadata_csv: str,
    output_csv: str,
    self_addresses: list[str] | None = None,
    automated_prefixes: list[str] | None = None,
    automated_domains: list[str] | None = None,
) -> int:
    csv_path = Path(inbox_metadata_csv)
    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    self_addrs = set((self_addresses or DEFAULT_SELF_ADDRESSES))
    prefixes = tuple(automated_prefixes or DEFAULT_AUTOMATED_PREFIXES)
    domains = tuple(automated_domains or DEFAULT_AUTOMATED_DOMAINS)

    people = defaultdict(lambda: {"total": 0, "sent": 0, "received": 0, "first": None, "last": None})

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sender = norm_email(row.get("from", ""))
            recipient = norm_email(row.get("to", ""))
            d = parse_date(row.get("date", ""))

            # SENT by you
            if sender in self_addrs:
                other = recipient
                direction = "sent"
            else:
                other = sender
                direction = "received"

            if not other or is_automated(other, self_addrs, prefixes, domains):
                continue

            rec = people[other]
            rec["total"] += 1
            if direction == "sent":
                rec["sent"] += 1
            else:
                rec["received"] += 1

            if d:
                if rec["first"] is None or d < rec["first"]:
                    rec["first"] = d
                if rec["last"] is None or d > rec["last"]:
                    rec["last"] = d

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["email", "total_messages", "sent_by_me", "received_by_me", "first_contact", "last_contact"])
        for email, rec in sorted(people.items(), key=lambda x: x[1]["total"], reverse=True):
            writer.writerow([
                email,
                rec["total"],
                rec["sent"],
                rec["received"],
                rec["first"].isoformat() if rec["first"] else "",
                rec["last"].isoformat() if rec["last"] else "",
            ])

    print(f"Done. {len(people)} human relationships written to {out_path}")
    return len(people)

def main():
    p = argparse.ArgumentParser(description="Extract relationship counts from inbox_metadata.csv.")
    p.add_argument("--in", dest="inp", default=str(Path("output")/"inbox_metadata.csv"), help="Input inbox_metadata.csv")
    p.add_argument("--out", default=str(Path("output")/"relationships_raw.csv"), help="Output relationships_raw.csv")
    args = p.parse_args()
    extract_relationships(args.inp, args.out)

if __name__ == "__main__":
    main()
