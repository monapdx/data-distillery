"""
Clean/merge relationships_filtered.csv into relationships_clean.csv.

Refactor notes:
- Removed hardcoded paths (CLI args).
- Logic unchanged.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


SYSTEM_DOMAINS = (
    "wordpress.com",
    "alerts.govtrack.us",
    "txt.voice.google.com",
    "getfreewrite.com",
    "my.simple.life",
)

SYSTEM_PREFIXES = (
    "wordpress@",
    "hello@",
    "bounces+",
)

def is_system(email: str) -> bool:
    e = email.lower()
    for p in SYSTEM_PREFIXES:
        if e.startswith(p):
            return True
    for d in SYSTEM_DOMAINS:
        if e.endswith("@" + d):
            return True
    return False

def canonical_email(email: str) -> str:
    e = email.lower()
    if "@gmail.com" in e:
        local, domain = e.split("@", 1)
        local = local.split("+", 1)[0].replace(".", "")
        return local + "@" + domain
    return e


def clean_relationships_csv(in_path: str, out_path: str):
    people = defaultdict(lambda: {
        "total": 0,
        "sent": 0,
        "recv": 0,
        "first": None,
        "last": None,
    })

    with open(in_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            email = r["email"]
            if is_system(email):
                continue

            canon = canonical_email(email)

            total = int(r["total_messages"])
            sent = int(r["sent_by_me"])
            recv = int(r["received_by_me"])

            people[canon]["total"] += total
            people[canon]["sent"] += sent
            people[canon]["recv"] += recv

            fc = r.get("first_contact")
            lc = r.get("last_contact")
            if fc:
                if people[canon]["first"] is None or fc < people[canon]["first"]:
                    people[canon]["first"] = fc
            if lc:
                if people[canon]["last"] is None or lc > people[canon]["last"]:
                    people[canon]["last"] = lc

    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)

    with outp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "email",
            "total_messages",
            "sent_by_me",
            "received_by_me",
            "first_contact",
            "last_contact",
        ])
        for email, r in sorted(people.items(), key=lambda x: x[1]["total"], reverse=True):
            writer.writerow([
                email,
                r["total"],
                r["sent"],
                r["recv"],
                r["first"] or "",
                r["last"] or "",
            ])

    print(f"Done. Cleaned relationships written to {outp}")
    print(f"Total cleaned relationships: {len(people)}")
    return str(outp)


def main():
    parser = argparse.ArgumentParser(description="Clean relationships_filtered.csv -> relationships_clean.csv")
    parser.add_argument("--in", dest="in_csv", default=str(Path("output") / "relationships_filtered.csv"))
    parser.add_argument("--out", default=str(Path("output") / "relationships_clean.csv"))
    args = parser.parse_args()
    clean_relationships_csv(args.in_csv, args.out)


if __name__ == "__main__":
    main()
