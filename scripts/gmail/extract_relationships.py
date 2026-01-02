"""
Build a 'relationships' table from inbox_metadata.csv.

Refactor notes:
- Removed hardcoded paths (now CLI args).
- Kept original logic, only wrapped into functions + main().
"""

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


# ---- CONFIG (defaults can be overridden via CLI) ----

DEFAULT_SELF_ADDRESSES = [
    "thegirlnextfloor@gmail.com",
    "ashly@ashlylorenzana.com",
]

DEFAULT_AUTOMATED_DOMAINS = [
    "facebookmail.com",
    "google.com",
    "googlemail.com",
    "craigslist.org",
    "nextdoor.com",
    "poshmark.com",
    "citychiconline.com",
    "havenly.com",
    "treasuremytext.com",
    "simple.life",
    "mail.havenly.com",
]

DEFAULT_AUTOMATED_PREFIXES = [
    "no-reply@",
    "noreply@",
    "notifications@",
    "support@",
    "help@",
]


# ---- HELPERS ----

def norm_email(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    if "<" in s and ">" in s:
        s = s.split("<")[-1].split(">")[0]
    return s.lower()

def is_automated(email: str, self_addresses, automated_domains, automated_prefixes) -> bool:
    if not email:
        return True
    if email in self_addresses:
        return True
    for p in automated_prefixes:
        if email.startswith(p):
            return True
    for d in automated_domains:
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
    out_csv: str,
    self_addresses=None,
    automated_domains=None,
    automated_prefixes=None,
):
    self_addresses = set(self_addresses or DEFAULT_SELF_ADDRESSES)
    automated_domains = tuple(automated_domains or DEFAULT_AUTOMATED_DOMAINS)
    automated_prefixes = tuple(automated_prefixes or DEFAULT_AUTOMATED_PREFIXES)

    people = defaultdict(lambda: {
        "total": 0,
        "sent": 0,
        "received": 0,
        "first": None,
        "last": None,
    })

    with open(inbox_metadata_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sender = norm_email(row.get("from", ""))
            recipient = norm_email(row.get("to", ""))
            d = parse_date(row.get("date", ""))

            # SENT by you
            if sender in self_addresses:
                other = recipient
                direction = "sent"
            else:
                other = sender
                direction = "received"

            if not other or is_automated(other, self_addresses, automated_domains, automated_prefixes):
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

    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "email",
            "total_messages",
            "sent_by_me",
            "received_by_me",
            "first_contact",
            "last_contact",
        ])
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
    return str(out_path)


def main():
    parser = argparse.ArgumentParser(description="Extract relationship counts from inbox metadata CSV.")
    parser.add_argument(
        "--in",
        dest="in_csv",
        default=str(Path("output") / "inbox_metadata.csv"),
        help="Path to inbox_metadata.csv (default: output/inbox_metadata.csv)",
    )
    parser.add_argument(
        "--out",
        default=str(Path("output") / "relationships_raw.csv"),
        help="Path to output relationships CSV (default: output/relationships_raw.csv)",
    )
    parser.add_argument(
        "--self",
        nargs="*",
        default=DEFAULT_SELF_ADDRESSES,
        help="Your own email addresses to treat as 'self' (space-separated list).",
    )
    args = parser.parse_args()
    extract_relationships(args.in_csv, args.out, self_addresses=args.self)


if __name__ == "__main__":
    main()
