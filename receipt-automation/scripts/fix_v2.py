#!/usr/bin/env python3
import xmlrpc.client
import csv
from collections import defaultdict
from datetime import datetime

URL = "http://localhost:8069"
DB = "tokoodoo13"
USER = "tokomakmur"
PASS = "admin123"

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PASS, {})
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

inv_acct = models.execute_kw(DB, uid, PASS, "account.account", "search", [[["code", "=", "112001"]]])[0]
ap_acct = models.execute_kw(DB, uid, PASS, "account.account", "search", [[["code", "=", "21100010"]]])[0]

def post(move_id):
    """Post a move, ignoring the None return"""
    try:
        models.execute_kw(DB, uid, PASS, "account.move", "action_post", [[move_id]])
    except xmlrpc.client.Fault:
        pass

def find_or_create(name):
    ids = models.execute_kw(DB, uid, PASS, "res.partner", "search", [[["name", "=", name]]])
    return ids[0] if ids else models.execute_kw(DB, uid, PASS, "res.partner", "create", [{"name": name, "supplier_rank": 1}])

def parse_date(d):
    try:
        return datetime.strptime(d.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")

# Reverse moves 2 and 3 (1 was already done)
for mid in [2, 3]:
    lines = models.execute_kw(DB, uid, PASS, "account.move.line", "search_read",
        [[["move_id", "=", mid]]], {"fields": ["name", "account_id", "debit", "credit"]})
    rev_lines = [(0, 0, {
        "name": "REV: " + l["name"],
        "account_id": l["account_id"][0],
        "debit": l["credit"],
        "credit": l["debit"],
    }) for l in lines]
    rev = {"ref": f"REV-{mid}", "date": datetime.now().strftime("%Y-%m-%d"), "journal_id": 1, "line_ids": rev_lines}
    rid = models.execute_kw(DB, uid, PASS, "account.move", "create", [rev])
    post(rid)
    print(f"Reversed move {mid} -> {rid}")

# Re-import correctly
csvs = [
    "/mnt/c/Users/kusum/Downloads/INV_2026_05598_odoo13.csv",
    "/mnt/c/Users/kusum/Downloads/NOTA_EO26032_odoo13.csv",
    "/mnt/c/Users/kusum/Downloads/NOTA_AK81357_odoo13.csv",
]

for path in csvs:
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    invs = defaultdict(list)
    for r in rows:
        invs[r["Invoice Number"].strip()].append(r)
    for inv, items in invs.items():
        s = items[0]["Supplier"].strip()
        d = parse_date(items[0].get("Date", ""))
        t = sum(float(r["Subtotal (Rp)"]) for r in items)
        p = find_or_create(s)
        ref = f"CORRECTED-{inv.replace('/', '-')}"
        ex = models.execute_kw(DB, uid, PASS, "account.move", "search", [[["ref", "=", ref]]])
        if ex:
            print(f"Skip {inv}")
            continue
        e = {"ref": ref, "date": d, "partner_id": p, "journal_id": 1, "line_ids": [
            (0, 0, {"name": f"Inv - {s}", "account_id": inv_acct, "debit": t, "credit": 0.0}),
            (0, 0, {"name": f"AP - {s}", "account_id": ap_acct, "debit": 0.0, "credit": t}),
        ]}
        eid = models.execute_kw(DB, uid, PASS, "account.move", "create", [e])
        post(eid)
        print(f"Corrected {inv} -> {eid} | Rp {t:,.0f}")

print("\nAll moves:")
for m in models.execute_kw(DB, uid, PASS, "account.move", "search_read", [[]],
    {"fields": ["name", "ref", "state", "amount_total"], "limit": 20}):
    print(f"  {m['name']} | {m['ref']} | {m['state']} | Rp {m['amount_total']}")
