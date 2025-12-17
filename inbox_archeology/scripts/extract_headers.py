import argparse
from pathlib import Path
import mailbox
import csv
from email.utils import parsedate_to_datetime

parser = argparse.ArgumentParser()
parser.add_argument("--mbox", required=True, help="Path to .mbox file")
parser.add_argument("--out", required=True, help="Output CSV path")
args = parser.parse_args()

mbox_path = Path(args.mbox)
output_path = Path(args.out)

# ✅ THIS IS THE CRITICAL LINE
output_path.parent.mkdir(parents=True, exist_ok=True)
mbox = mailbox.mbox(mbox_path)



with open(output_path, "w", newline="", encoding="utf-8") as f:

    writer = csv.writer(f)
    writer.writerow([
        "date",
        "from",
        "to",
        "subject",
        "message_id",
        "in_reply_to"
    ])

    count = 0
    for msg in mbox:
        try:
            date = parsedate_to_datetime(msg.get("Date"))
        except:
            date = None

        writer.writerow([
            date,
            msg.get("From"),
            msg.get("To"),
            msg.get("Subject"),
            msg.get("Message-ID"),
            msg.get("In-Reply-To")
        ])

        count += 1
        if count % 10000 == 0:
            print(f"{count} messages processed...")

print("Done.")
