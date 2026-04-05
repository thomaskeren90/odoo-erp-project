#!/usr/bin/env python3
"""
Odoo 13 Product Importer — via XML-RPC
Run this from your WSL machine where Odoo is running.

Usage:
    python3 import_to_odoo.py
"""

import xmlrpc.client
import csv
import time
import sys

# === CONFIG ===
ODOO_URL = "http://localhost:8069"
ODOO_DB = "tokoodoo13"
ODOO_USER = "tokomakmur"
ODOO_PASS = "admin"

CSV_FILE = "odoo13_product_import_final.csv"

# === CONNECT ===
print(f"Connecting to {ODOO_URL} ...")
common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
if not uid:
    print("❌ Authentication failed! Check DB/user/password.")
    sys.exit(1)
print(f"✅ Connected as uid={uid}")

models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

# === HELPERS ===
def execute(model, method, *args):
    return models.execute_kw(ODOO_DB, uid, ODOO_PASS, model, method, *args)

def get_or_create_category(name):
    """Get or create product category"""
    cat_ids = execute('product.category', 'search', [[['name', '=', name]]])
    if cat_ids:
        return cat_ids[0]
    cat_id = execute('product.category', 'create', [{'name': name}])
    print(f"  Created category: {name}")
    return cat_id

def get_category_id(name):
    """Get category, create if needed"""
    return get_or_create_category(name)

# === STEP 1: Create categories first ===
print("\n📁 Creating categories...")
csv_rows = []
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    csv_rows = list(reader)

categories = sorted(set(r['Category'] for r in csv_rows))
cat_cache = {}
for cat in categories:
    cat_cache[cat] = get_category_id(cat)

print(f"  {len(cat_cache)} categories ready.")

# === STEP 2: Import products in batches ===
BATCH_SIZE = 100
total = len(csv_rows)
created = 0
skipped = 0
errors = []

print(f"\n📦 Importing {total} products (batches of {BATCH_SIZE})...")

for batch_start in range(0, total, BATCH_SIZE):
    batch = csv_rows[batch_start:batch_start + BATCH_SIZE]
    batch_data = []
    
    for r in batch:
        # Check if product already exists by internal reference
        existing = execute('product.template', 'search', [[['default_code', '=', r['Internal Reference']]]])
        if existing:
            skipped += 1
            continue
        
        vals = {
            'name': r['Name'][:128],
            'default_code': r['Internal Reference'],
            'barcode': r['Barcode'],
            'type': 'product',  # Storable Product
            'categ_id': cat_cache.get(r['Category'], 1),
            'list_price': float(r['Sales Price']) if r['Sales Price'] else 0,
            'standard_price': float(r['Cost']) if r['Cost'] else 0,
            'sale_ok': True,
            'purchase_ok': True,
        }
        batch_data.append(vals)
    
    # Create batch
    for vals in batch_data:
        try:
            pid = execute('product.template', 'create', [vals])
            created += 1
            if created % 50 == 0:
                print(f"  Progress: {created}/{total} created, {skipped} skipped")
        except Exception as e:
            errors.append(f"{vals.get('default_code', '?')}: {e}")
            skipped += 1
    
    time.sleep(0.1)  # Small delay between batches

# === STEP 3: Set stock quantities ===
print(f"\n📊 Setting stock quantities...")
stock_set = 0
for r in csv_rows:
    if not r['Quantity On Hand'] or r['Quantity On Hand'] == '0':
        continue
    
    try:
        # Find product
        prod_ids = execute('product.product', 'search', [[['default_code', '=', r['Internal Reference']]]])
        if not prod_ids:
            continue
        
        qty = int(r['Quantity On Hand'])
        
        # Get stock location
        stock_loc = execute('stock.location', 'search', [[['usage', '=', 'internal']]], {'limit': 1})
        if not stock_loc:
            continue
        
        # Create inventory adjustment
        vals = {
            'product_id': prod_ids[0],
            'location_id': stock_loc[0],
            'new_quantity': qty,
        }
        # For Odoo 13, we use stock.change.product.qty
        change_id = execute('stock.change.product.qty', 'create', [vals])
        execute('stock.change.product.qty', 'change_product_qty', [change_id])
        stock_set += 1
        
        if stock_set % 100 == 0:
            print(f"  Stock set: {stock_set}")
    except Exception as e:
        errors.append(f"stock {r.get('Internal Reference', '?')}: {e}")

# === SUMMARY ===
print(f"\n{'='*50}")
print(f"✅ IMPORT COMPLETE")
print(f"{'='*50}")
print(f"  Created:     {created}")
print(f"  Skipped:     {skipped}")
print(f"  Stock set:   {stock_set}")
print(f"  Errors:      {len(errors)}")

if errors:
    print(f"\n⚠️  First 10 errors:")
    for e in errors[:10]:
        print(f"  {e}")

print(f"\n🔗 Check your products at: {ODOO_URL}/web#action=401")
