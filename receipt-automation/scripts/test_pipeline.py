#!/usr/bin/env python3
"""
End-to-end pipeline test.
Usage: python3 test_pipeline.py <image_path> [cogs|expense]
"""
import sys
import json
import subprocess
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_step(name, cmd):
    print(f"\n{'='*50}")
    print(f"📌 {name}")
    print(f"{'='*50}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed: {result.stderr}")
        sys.exit(1)
    print(result.stdout)
    return result.stdout.strip()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_pipeline.py <image_path> [cogs|expense]")
        sys.exit(1)

    image_path = sys.argv[1]
    entry_type = sys.argv[2] if len(sys.argv) > 2 else None

    # Step 1: OCR
    ocr_output = run_step("OCR Parsing", [
        "python3", os.path.join(SCRIPT_DIR, "ocr_parser.py"), image_path
    ])
    receipt = json.loads(ocr_output)

    if not receipt.get("is_readable", True):
        print("❌ Image is not a readable receipt")
        sys.exit(1)

    print(f"\n📋 Receipt: {receipt['vendor']} — {receipt['currency']} {receipt['total_amount']}")

    # Step 2: Ask user if not provided
    if not entry_type:
        print(f"\n❓ Is this COGS or Expense?")
        print(f"   COGS = inventory purchase (DR Inventory + DR COGS / CR AP)")
        print(f"   Expense = operating cost (DR Expense / CR Bank)")
        entry_type = input("   Type 'cogs' or 'expense': ").strip().lower()

    # Step 3: Save receipt JSON
    receipt_path = "/tmp/receipt_parsed.json"
    with open(receipt_path, "w") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)

    # Step 4: Push to Odoo
    odoo_output = run_step("Push to Odoo", [
        "python3", os.path.join(SCRIPT_DIR, "odoo_pusher.py"), receipt_path, entry_type
    ])

    # Extract entry ID from output
    entry_id = odoo_output.split("ID ")[-1].split("\n")[0] if "ID " in odoo_output else "0"

    # Step 5: Log to CSV
    run_step("CSV Log", [
        "python3", os.path.join(SCRIPT_DIR, "csv_logger.py"), receipt_path, entry_type, entry_id
    ])

    print(f"\n{'='*50}")
    print(f"🎉 Pipeline complete!")
    print(f"{'='*50}")
