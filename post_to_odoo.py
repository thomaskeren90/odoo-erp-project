import xmlrpc.client, sys
from datetime import datetime
url = "http://localhost:8069"
db = "tokoodoo13"
user = "tokomakmur"
password = "admin123"
JOURNAL_BCA = 10
common = xmlrpc.client.ServerProxy(url + "/xmlrpc/2/common")
uid = common.authenticate(db, user, password, {})
models = xmlrpc.client.ServerProxy(url + "/xmlrpc/2/object")
def get_account_id(code):
    ids = models.execute_kw(db, uid, password, "account.account", "search", [[["code", "=", code]]])
    return ids[0] if ids else None
def get_bank_account():
    ids = models.execute_kw(db, uid, password, "account.account", "search_read", [[["user_type_id", "=", 3]]], {"fields": ["id", "name"], "limit": 1})
    return ids[0]["id"] if ids else None
def post_entry(date_str, desc, amount, cr_db, account_code, journal_id):
    bank_id = get_bank_account()
    contra_id = get_account_id(account_code)
    if not contra_id or not bank_id:
        print(f"  SKIP: {account_code} not found")
        return None
    try:
        try:
            ds = date_str.replace(chr(39), "").strip()
            if len(ds) <= 5:
                ds = ds + "/2026"
            elif len(ds) == 7 and int(ds[3:5]) <= 4:
                ds = ds + "/2026"
            elif len(ds) == 7:
                ds = ds + "/2025"
            d = datetime.strptime(ds, "%d/%m/%Y")
        date_fmt = d.strftime("%Y-%m-%d")
    except:
        date_fmt = datetime.now().strftime("%Y-%m-%d")
    debit_acc = bank_id if cr_db == "CR" else contra_id
    credit_acc = contra_id if cr_db == "CR" else bank_id
    move_id = models.execute_kw(db, uid, password, "account.move", "create", [{"journal_id": journal_id, "date": date_fmt, "ref": desc[:80], "line_ids": [(0, 0, {"account_id": debit_acc, "name": desc[:80], "debit": amount, "credit": 0}), (0, 0, {"account_id": credit_acc, "name": desc[:80], "debit": 0, "credit": amount})]}])
    models.execute_kw(db, uid, password, "account.move", "action_post", [[move_id]])
    return move_id
import importlib.util
spec = importlib.util.spec_from_file_location("bank_automation", "bank_automation.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
bca_file = sys.argv[1] if len(sys.argv) > 1 else None
if not bca_file:
    print("Usage: python3 post_to_odoo.py <bca_csv>")
    exit()
txs = mod.parse_bca_csv(bca_file)
posted = 0
skipped = 0
for tx in txs:
    if mod.is_own_transfer(tx["desc"], tx["amount"]):
        skipped += 1
        continue
    account_code, account_name = mod.classify_transaction(tx["desc"])
    if not account_code:
        print(f"  UNCLASSIFIED: {tx['date']} {tx['desc'][:50]}")
        continue
    move_id = post_entry(tx["date"], tx["desc"], tx["amount"], tx["cr_db"], account_code, JOURNAL_BCA)
    if move_id:
        print(f"  POSTED: {tx['date']} {tx['cr_db']} {tx['amount']:,.0f} -> {account_code} move:{move_id}")
        posted += 1
print(f"Done! Posted:{posted} Skipped:{skipped}")
