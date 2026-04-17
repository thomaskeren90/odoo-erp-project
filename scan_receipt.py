#!/usr/bin/env python3
"""
Receipt Scanner - CLI (Ollama)
Usage: python3 scan_receipt.py /path/to/receipt.jpg
"""
import sys, os, json, re, base64, requests, xmlrpc.client
from datetime import datetime

exec(open(os.path.join(os.path.dirname(__file__), 'config.py')).read())

def scan(image_path):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    prompt = """Extract receipt data as JSON only, no markdown, no explanation:
{"supplier":"shop name","date":"YYYY-MM-DD","total":150000,"notes":"any extra info","confidence":"high/medium/low"}
Rules: Remove Rp and dots from amounts (Rp 150.00 = 15000). Use null if unclear."""

    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "images": [b64],
            "stream": False,
            "options": {"temperature": 0.1}
        },
        timeout=120
    )
    resp.raise_for_status()
    text = resp.json()["response"]

    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    match = re.search(r'\{[\s\S]*\}', text)
    data = json.loads(match.group()) if match else {"raw": text}

    if data.get("total"):
        total = str(data["total"])
        total = re.sub(r'[^\d]', '', total)
        data["total"] = int(total) if total else 0

    return data

def save_to_odoo(data, entry_type="expense"):
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODO_USERNAME, ODOO_PASSWORD, {})
    if not uid:
        print("❌ Odoo login failed!")
        return None
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    supplier = data.get('supplier', 'Unknown') or 'Unknown'
    partners = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'search_read',
        [[('name', '=', supplier)]], {'fields': ['id'], 'limit': 1})
    partner_id = partners[0]['id'] if partners else models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
        'res.partner', 'create', [{'name': supplier, 'supplier_rank': 1}])

    total = data.get('total', 0) or 0

    vals = {
        'move_type': 'in_invoice',
        'partner_id': partner_id,
        'invoice_date': data.get('date') or datetime.now().strftime('%Y-%m-%d'),
        'ref': data.get('notes', 'Receipt scan'),
        'invoice_line_ids': [(0, 0, {
            'name': data.get('notes', entry_type + ' from receipt'),
            'quantity': 1,
            'price_unit': total,
        })]
    }
    move_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'account.move', 'create', [vals])
    return move_id

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 scan_receipt.py <image_path>")
        sys.exit(1)

    img = sys.argv[1]
    if not os.path.exists(img):
        print(f"❌ File not found: {img}")
        sys.exit(1)

    print(f"📸 Scanning: {img}")
    print(f"🤖 Using: {OLLAMA_MODEL}")
    data = scan(img)

    print(f"\n📄 Extracted:")
    print(f"   Supplier: {data.get('supplier')}")
    print(f"   Date:     {data.get('date')}")
    print(f"   Total:    Rp {data.get('total', 0):,}")
    print(f"   Notes:    {data.get('notes')}")
    print(f"   Confidence: {data.get('confidence')}")

    choice = input("\n💰 Expense or 📦 COGS? (e/c): ").strip().lower()
    entry_type = "cogs" if choice == "c" else "expense"

    move_id = save_to_odoo(data, entry_type)
    if move_id:
        print(f"\n✅ Saved to Odoo! Bill ID: {move_id}")
    else:
        print("\n❌ Failed to save to Odoo")
