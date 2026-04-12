#!/usr/bin/env python3
"""Reverse the 3 doubled COGS entries and re-import correctly."""
import xmlrpc.client
import csv
import sys
from collections import defaultdict
from datetime import datetime

URL = "http://localhost:8069"
DB = "tokoodoo13"
USER = "tokomakmur"
PASS = "admin123"

ACCT_INVENTORY = "112001"
ACCT_AP = "21100010"

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PASS, {})
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

# === STEP 1: Reverse the 3 bad entries ===
print("=== STEP 1: Reversing incorrect entries ===\n")

move_ids = models.execute_kw(DB, uid, PASS,
    "account.move", "search", [[]])

moves = models.execute_kw(DB, uid, PASS,
    "account.move", "search_read",
    [[["id", "in", move_ids]]],
    {"fields": ["id", "name", "ref", "date", "state", "line_ids"]})

for move in moves:
    ref = move.get("ref", "")
    if not ref.startswith("COGS-"):
        continue

    move_id = move["id"]
    print(f"Reversing: {move['name']} (ref: {ref})")

    # Get line details
    lines = models.execute_kw(DB, uid, PASS,
        "account.move.line", "search_read",
        [[["move_id", "=", move_id]]],
        {"fields": ["name", "account_id", "debit", "credit"]})

    # Create reversal lines (swap debit/credit)
    reversal_lines = []
    for line in lines:
        reversal_lines.append((0, 0, {
            "name": f"REVERSAL: {line['name']}",
            "account_id": line["account_id"][0],
            "debit": line["credit"],
            "credit": line["debit"],
        }))

    reversal = {
        "ref": f"REVERSAL-{ref}",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "journal_id": 1,
        "line_ids": reversal_lines,
    }

    rev_id = models.execute_kw(DB, uid, PASS,
        "account.move", "create", [reversal])
    models.execute_kw(DB, uid, PASS,
        "account.move", "action_post", [[rev_id]])
    print(f"  -> Reversal move ID: {rev_id}")

    # Also cancel the original
    models.execute_kw(DB, uid, PASS,
        "account.move", "button_draft", [[move_id]])
    models.execute_kw(DB, uid, PASS,
        "account.move", "button_cancel", [[move_id]])
    print(f"  -> Original {move['name']} cancelled")

print("\n=== STEP 2: Re-importing correctly ===\n")

inv_acct = models.execute_kw(DB, uid, PASS,
    "account.account", "search", [[["code", "=", ACCT_INVENTORY]]])[0]
ap_acct = models.execute_kw(DB, uid, PASS,
    "account.account", "search", [[["code", "=", ACCT_AP]]])[0]


def find_or_create_partner(name):
    ids = models.execute_kw(DB, uid, PASS,
        "res.partner", "search", [[["name", "=", name]]])
    if ids:
        return ids[0]
    return models.execute_kw(DB, uid, PASS,
        "res.partner", "create", [{"name": name, "supplier_rank": 1}])


def parse_date(d):
    try:
        return datetime.strptime(d.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")


def import_csv(csv_path):
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    invoices = defaultdict(list)
    for row in rows:
        invoices[row.get("Invoice Number", "").strip()].append(row)

    for inv_no, items in invoices.items():
        first = items[0]
        supplier = first.get("Supplier", "Unknown").strip()
        date = parse_date(first.get("Date", ""))
        total = sum(float(r.get("Subtotal (Rp)", 0)) for r in items)
        partner_id = find_or_create_partner(supplier)

        ref = f"CORRECTED-{inv_no.replace('/', '-')}"

        # Check duplicate
        existing = models.execute_kw(DB, uid, PASS,
            "account.move", "search", [[["ref", "=", ref]]])
        if existing:
            print(f"Skipping {inv_no} — already re-imported")
            continue

        # Correct entry: DR Inventory / CR AP
        entry = {
            "ref": ref,
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
                    "name": f"AP — {supplier} ({inv_no})",
                    "account_id": ap_acct,
                    "debit": 0.0,
                    "credit": total,
                }),
            ],
        }

        entry_id = models.execute_kw(DB, uid, PASS,
            "account.move", "create", [entry])
        models.execute_kw(DB, uid, PASS,
            "account.move", "action_post", [[entry_id]])

        print(f"Corrected {inv_no} -> Move ID: {entry_id} | {supplier} | Rp {total:,.0f}")


csvs = [
    "/mnt/c/Users/kusum/Downloads/INV_2026_05598_odoo13.csv",
    "/mnt/c/Users/kusum/Downloads/NOTA_EO26032_odoo13.csv",
    "/mnt/c/Users/kusum/Downloads/NOTA_AK81357_odoo13.csv",
]

for f in csvs:
    print(f"\nProcessing: {f}")
    import_csv(f)

print("\nDone! Verify with:")
print('python3 -c "')
print("""import xmlrpc.client
c = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/common')
u = c.authenticate('tokoodoo13','tokomakmur','admin123',{})
m = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/object')
for x in m.execute_kw('tokoodoo13',u,'admin123','account.move','search_read',[[]],{'fields':['name','ref','date','state','amount_total'],'limit':20}):
    print(f"  {x['name']} | {x['ref']} | {x['date']} | {x['state']} | Rp {x['amount_total']}")""")
print('"')
