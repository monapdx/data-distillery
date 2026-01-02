"""
Extract basic headers from a Gmail MBOX into a CSV.

Portable behavior:
- If --mbox is not provided, auto-detect a single *.mbox file in input/
- Default output: output/inbox_metadata.csv
"""

import argparse
import csv
import mailbox
from email.utils import parsedate_to_datetime
from pathlib import Path


def find_default_mbox(input_dir: Path) -> Path:
    input_dir.mkdir(parents=True, exist_ok=True)
    candidates = sorted(input_dir.glob("*.mbox"))

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) == 0:
        raise FileNotFoundError(
            "No .mbox file found.\n"
            f"Put your file here: {input_dir.resolve()}\n"
            "Example: pipelines/gmail/input/mail.mbox\n"
            "Or run with: --mbox path\\to\\file.mbox"
        )

    names = "\n".join(f"- {p.name}" for p in candidates)
    raise FileExistsError(
        "Multiple .mbox files found in input/. Please keep only one, or pass --mbox.\n"
        f"Found:\n{names}"
    )


def extract_headers(mbox_path: str, output_csv: str, progress_every: int = 10000) -> int:
    mbox = mailbox.mbox(mbox_path)
    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "from", "to", "subject", "message_id", "in_reply_to"])

        for msg in mbox:
            try:
                date = parsedate_to_datetime(msg.get("Date"))
            except Exception:
                date = None

            writer.writerow(
                [
                    date,
                    msg.get("From"),
                    msg.get("To"),
                    msg.get("Subject"),
                    msg.get("Message-ID"),
                    msg.get("In-Reply-To"),
                ]
            )

            count += 1
            if progress_every and count % progress_every == 0:
                print(f"{count} messages processed...")

    print(f"Done. Wrote: {out_path}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Extract headers from an MBOX into a CSV.")
    parser.add_argument("--mbox", default=None, help="Path to the input .mbox file (optional)")
    parser.add_argument(
        "--out",
        default=str(Path("output") / "inbox_metadata.csv"),
        help="Path to output CSV (default: output/inbox_metadata.csv)",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10000,
        help="Print progress every N messages (default: 10000). Use 0 to disable.",
    )
    args = parser.parse_args()

    if args.mbox:
        mbox_path = Path(args.mbox)
    else:
        mbox_path = find_default_mbox(Path("input"))

    extract_headers(str(mbox_path), args.out, args.progress_every)


if __name__ == "__main__":
    main()
