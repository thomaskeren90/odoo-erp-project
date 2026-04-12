#!/usr/bin/env python3
"""
CSV to Odoo Importer — Reads receipt CSVs and creates COGS journal entries in Odoo 13.
Usage: python3 csv_to_odoo.py <csv_file1> [csv_file2] ...
"""
import sys
import csv
import xmlrpc.client
from collections import defaultdict
from datetime import datetime

ODOO_URL = "http://localhost:8069"
ODOO_DB = "tokoodoo13"
ODOO_USER = "tokomakmur"
ODOO_PASS = "admin123"

# === Account codes — adjust to match your Odoo COA ===
ACCT_INVENTORY = "101000"
ACCT_AP = "211100"
ACCT_COGS = "501000"


def connect():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
    if not uid:
        raise Exception("❌ Auth failed")
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models


def find_account(uid, models, code):
    ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'account.account', 'search', [[['code', '=', code]]])
    if not ids:
        raise Exception(f"❌ Account {code} not found — check your Chart of Accounts in Odoo")
    return ids[0]


def find_or_create_partner(uid, models, name):
    ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'res.partner', 'search', [[['name', '=', name]]])
    if ids:
        return ids[0]
    pid = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'res.partner', 'create', [{"name": name, "supplier_rank": 1}])
    print(f"   ✨ Created partner: {name} (ID: {pid})")
    return pid


def parse_date(date_str):
    """Parse DD/MM/YYYY to YYYY-MM-DD"""
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")


def import_csv(uid, models, csv_path):
    """Import a single CSV file into Odoo as a COGS journal entry."""

    # Read CSV rows
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print(f"⚠️  Empty file: {csv_path}")
        return

    # Group by invoice
    invoices = defaultdict(list)
    for row in rows:
        inv_no = row.get("Invoice Number", "").strip()
        invoices[inv_no].append(row)

    inv_acct = find_account(uid, models, ACCT_INVENTORY)
    ap_acct = find_account(uid, models, ACCT_AP)
    cogs_acct = find_account(uid, models, ACCT_COGS)

    for inv_no, items in invoices.items():
        first = items[0]
        supplier = first.get("Supplier", "Unknown").strip()
        date = parse_date(first.get("Date", ""))
        total = sum(float(r.get("Subtotal (Rp)", 0)) for r in items)

        partner_id = find_or_create_partner(uid, models, supplier)

        # Build line items with descriptions
        descriptions = []
        for item in items:
            qty = item.get("Quantity", "1")
            name = item.get("Product Name", "Item")
            subtotal = item.get("Subtotal (Rp)", "0")
            descriptions.append(f"{qty}x {name} = Rp {subtotal}")

        inv_ref = f"COGS-{inv_no.replace('/', '-')}"

        # Check if already imported
        existing = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
            'account.move', 'search', [[['ref', '=', inv_ref]]])
        if existing:
            print(f"⏭️  Skipping {inv_no} — already imported (move ID: {existing[0]})")
            continue

        # Journal entry: DR Inventory + DR COGS / CR AP
        journal_entry = {
            "ref": inv_ref,
            "date": date,
            "partner_id": partner_id,
            "journal_id": 1,
            "line_ids": [
                (0, 0, {
                    "name": f"Inventory — {supplier} ({inv_no})",
                    "account_id": inv_acct,
                    "debit": total,
                    "credit": 0.0,
                }),
                (0, 0, {
                    "name": f"COGS — {supplier} ({inv_no})",
                    "account_id": cogs_acct,
                    "debit": total,
                    "credit": 0.0,
                }),
                (0, 0, {
                    "name": f"AP — {supplier} ({inv_no})",
                    "account_id": ap_acct,
                    "debit": 0.0,
                    "credit": total * 2,  # balances both debits
                }),
            ],
        }

        entry_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
            'account.move', 'create', [journal_entry])

        models.execute_kw(ODOO_DB, uid, ODOO_PASS,
            'account.move', 'action_post', [[entry_id]])

        print(f"✅ {inv_no} → Move ID: {entry_id} | {supplier} | Rp {total:,.0f}")
        for d in descriptions:
            print(f"   └─ {d}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 csv_to_odoo.py <file1.csv> [file2.csv ...]")
        sys.exit(1)

    uid, models = connect()
    print(f"🔗 Connected to Odoo (uid: {uid})\n")

    for csv_file in sys.argv[1:]:
        print(f"📄 Processing: {csv_file}")
        import_csv(uid, models, csv_file)
        print()

    print("🎉 Done!")
