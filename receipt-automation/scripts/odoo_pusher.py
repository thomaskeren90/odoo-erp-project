#!/usr/bin/env python3
"""
Odoo Pusher — Creates journal entries in Odoo 13 from parsed receipt JSON.
Run: python3 odoo_pusher.py <receipt.json> <entry_type: cogs|expense>
"""
import sys
import json
import xmlrpc.client
from datetime import datetime

# === CONFIG (override via .env or edit here) ===
ODOO_URL = "http://localhost:8069"
ODOO_DB = "tokoodoo13"
ODOO_USER = "tokomakmur"
ODOO_PASS = "admin123"

# === Chart of Accounts (adjust to match your COA) ===
ACCOUNTS = {
    # Assets
    "inventory":    {"code": "101000", "name": "Inventory"},
    "bank":         {"code": "101200", "name": "Bank"},
    # Liabilities
    "ap_trade":     {"code": "211100", "name": "Account Payable"},
    # Expenses
    "cogs":         {"code": "501000", "name": "Cost of Goods Sold"},
    "opex":         {"code": "611000", "name": "Operating Expenses"},
    "office":       {"code": "611100", "name": "Office Supplies"},
    "transport":    {"code": "611200", "name": "Transportation"},
    "utilities":    {"code": "611300", "name": "Utilities"},
}


def connect():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
    if not uid:
        raise Exception("❌ Odoo auth failed")
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models


def find_or_create_partner(models, uid, vendor_name):
    """Find existing partner or create new one"""
    partner_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'res.partner', 'search',
        [[['name', '=', vendor_name]]])

    if partner_ids:
        return partner_ids[0]

    partner_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'res.partner', 'create',
        [{"name": vendor_name, "supplier_rank": 1}])
    print(f"   Created partner: {vendor_name} (ID: {partner_id})")
    return partner_id


def find_account_by_code(models, uid, code):
    """Find account ID by account code"""
    account_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'account.account', 'search',
        [[['code', '=', code]]])
    if not account_ids:
        raise Exception(f"❌ Account with code {code} not found in Odoo")
    return account_ids[0]


def create_expense_entry(models, uid, receipt, partner_id):
    """
    Expense journal entry:
    DR: Expense Account (6xxxxx)
    CR: Bank (101200) or AP (211100)
    """
    amount = receipt["total_amount"]
    date = receipt.get("date") or datetime.now().strftime("%Y-%m-%d")
    vendor = receipt["vendor"]
    ref = receipt.get("receipt_number") or f"EXP-{datetime.now().strftime('%Y%m%d%H%M')}"

    debit_account = find_account_by_code(models, uid, ACCOUNTS["opex"]["code"])
    credit_account = find_account_by_code(models, uid, ACCOUNTS["bank"]["code"])

    journal_entry = {
        "ref": ref,
        "date": date,
        "journal_id": 1,  # Miscellaneous Journal — adjust if needed
        "line_ids": [
            (0, 0, {
                "name": f"Expense - {vendor}",
                "account_id": debit_account,
                "debit": amount,
                "credit": 0.0,
            }),
            (0, 0, {
                "name": f"Payment - {vendor}",
                "account_id": credit_account,
                "debit": 0.0,
                "credit": amount,
            }),
        ],
    }

    entry_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'account.move', 'create', [journal_entry])

    # Post the journal entry
    models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'account.move', 'action_post', [[entry_id]])

    return entry_id


def create_cogs_entry(models, uid, receipt, partner_id):
    """
    COGS journal entry (3-way):
    DR: Inventory (101000)
    DR: COGS (501000)
    CR: Account Payable (211100) — total amount owed
    """
    amount = receipt["total_amount"]
    date = receipt.get("date") or datetime.now().strftime("%Y-%m-%d")
    vendor = receipt["vendor"]
    ref = receipt.get("receipt_number") or f"COGS-{datetime.now().strftime('%Y%m%d%H%M')}"

    inventory_acct = find_account_by_code(models, uid, ACCOUNTS["inventory"]["code"])
    cogs_acct = find_account_by_code(models, uid, ACCOUNTS["cogs"]["code"])
    ap_acct = find_account_by_code(models, uid, ACCOUNTS["ap_trade"]["code"])

    journal_entry = {
        "ref": ref,
        "date": date,
        "journal_id": 1,
        "line_ids": [
            (0, 0, {
                "name": f"Inventory receipt - {vendor}",
                "account_id": inventory_acct,
                "debit": amount,
                "credit": 0.0,
            }),
            (0, 0, {
                "name": f"COGS - {vendor}",
                "account_id": cogs_acct,
                "debit": amount,
                "credit": 0.0,
            }),
            (0, 0, {
                "name": f"AP - {vendor}",
                "account_id": ap_acct,
                "debit": 0.0,
                "credit": amount * 2,  # balancing both debits
            }),
        ],
    }

    entry_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'account.move', 'create', [journal_entry])

    models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'account.move', 'action_post', [[entry_id]])

    return entry_id


def push_to_odoo(receipt_json: dict, entry_type: str):
    uid, models = connect()

    vendor = receipt_json.get("vendor", "Unknown Vendor")
    partner_id = find_or_create_partner(models, uid, vendor)

    if entry_type == "expense":
        entry_id = create_expense_entry(models, uid, receipt_json, partner_id)
        print(f"✅ Expense entry created: ID {entry_id}")
    elif entry_type == "cogs":
        entry_id = create_cogs_entry(models, uid, receipt_json, partner_id)
        print(f"✅ COGS entry created: ID {entry_id}")
    else:
        print(f"❌ Unknown entry type: {entry_type}", file=sys.stderr)
        sys.exit(1)

    return entry_id


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 odoo_pusher.py <receipt.json> <cogs|expense>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        receipt = json.load(f)

    entry_type = sys.argv[2].lower()
    push_to_odoo(receipt, entry_type)
