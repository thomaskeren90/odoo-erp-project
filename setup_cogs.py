import xmlrpc.client
URL = "http://localhost:8069"
DB = "tokoodoo13"
USER = "tokomakmur"
PASS = "admin123"
common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PASS, {})
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
expense_type = models.execute_kw(DB, uid, PASS, "account.account.type", "search_read", [[["name", "ilike", "expense"]]], {"fields": ["id", "name"], "limit": 5})
print("Expense types:", expense_type)
cogs_id = models.execute_kw(DB, uid, PASS, "account.account", "create", [{"code": "50100010", "name": "Harga Pokok Penjualan (COGS)", "user_type_id": expense_type[0]["id"] if expense_type else 15, "reconcile": False}])
print(f"Created COGS: 50100010 (ID: {cogs_id})")
accounts = models.execute_kw(DB, uid, PASS, "account.account", "search_read", [[["code", "in", ["112001", "21100010", "50100010"]]]], {"fields": ["code", "name"]})
print("Ready:")
for a in accounts:
    print(f"  {a['code']} - {a['name']}")
