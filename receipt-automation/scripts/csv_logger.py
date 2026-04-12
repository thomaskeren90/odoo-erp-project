#!/usr/bin/env python3
"""
CSV Logger — Appends receipt data to daily CSV for audit trail.
Run: python3 csv_logger.py <receipt.json> <entry_type> <odoo_entry_id>
"""
import sys
import json
import csv
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def log_receipt(receipt: dict, entry_type: str, odoo_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path = os.path.join(LOG_DIR, f"receipts-{today}.csv")

    file_exists = os.path.exists(csv_path)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "vendor", "date", "total_amount",
                "currency", "entry_type", "odoo_entry_id",
                "receipt_number", "line_items_json"
            ])

        writer.writerow([
            datetime.now().isoformat(),
            receipt.get("vendor", ""),
            receipt.get("date", ""),
            receipt.get("total_amount", 0),
            receipt.get("currency", "IDR"),
            entry_type,
            odoo_id,
            receipt.get("receipt_number", ""),
            json.dumps(receipt.get("line_items", []), ensure_ascii=False),
        ])

    print(f"📋 Logged to {csv_path}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 csv_logger.py <receipt.json> <cogs|expense> <odoo_entry_id>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        receipt = json.load(f)

    log_receipt(receipt, sys.argv[2], int(sys.argv[3]))
