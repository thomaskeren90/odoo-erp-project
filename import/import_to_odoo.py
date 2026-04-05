#!/usr/bin/env python3
"""
Odoo 13 Product Importer — via XML-RPC
Run from your laptop where Odoo is running.

Usage:
    pip install requests  # not needed, xmlrpc is built-in
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

def execute(model, method, *args):
    return models.execute_kw(ODOO_DB, uid, ODOO_PASS, model, method, *args)

def get_or_create_category(name):
    cat_ids = execute('product.category', 'search', [[['name', '=', name]]])
    if cat_ids:
        return cat_ids[0]
    cat_id = execute('product.category', 'create', [{'name': name}])
    print(f"  Created category: {name}")
    return cat_id

# === READ CSV ===
print(f"\n📄 Reading {CSV_FILE} ...")
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    csv_rows = list(reader)
print(f"  {len(csv_rows)} rows found")

# === STEP 1: Categories ===
print("\n📁 Creating categories...")
categories = sorted(set(r['Category'] for r in csv_rows))
cat_cache = {}
for cat in categories:
    cat_cache[cat] = get_or_create_category(cat)
print(f"  {len(cat_cache)} categories ready")

# === STEP 2: Import products ===
BATCH_SIZE = 50
total = len(csv_rows)
created = 0
skipped = 0
errors = []

print(f"\n📦 Importing {total} products (batches of {BATCH_SIZE})...")

for batch_start in range(0, total, BATCH_SIZE):
    batch = csv_rows[batch_start:batch_start + BATCH_SIZE]
    
    for r in batch:
        sku = r['Internal Reference'].strip()
        if not sku:
            skipped += 1
            continue
        
        # Check if exists
        existing = execute('product.template', 'search', [[['default_code', '=', sku]]])
        if existing:
            skipped += 1
            continue
        
        name = r['Name'][:128].strip()
        barcode = r['Barcode'].strip() if r['Barcode'] else False
        price = float(r['Sales Price']) if r['Sales Price'] else 0
        cost = float(r['Cost']) if r['Cost'] else 0
        cat_name = r['Category'].strip()
        
        vals = {
            'name': name,
            'default_code': sku,
            'barcode': barcode,
            'type': 'product',  # Storable Product
            'categ_id': cat_cache.get(cat_name, 1),
            'list_price': price,
            'standard_price': cost,
            'sale_ok': True,
            'purchase_ok': True,
        }
        
        try:
            pid = execute('product.template', 'create', [vals])
            created += 1
            if created % 100 == 0:
                print(f"  ⏳ {created}/{total} created, {skipped} skipped")
        except Exception as e:
            errors.append(f"{sku}: {e}")
            skipped += 1
    
    time.sleep(0.05)

# === STEP 3: Set stock quantities (Odoo 13 compatible) ===
print(f"\n📊 Setting stock quantities...")
stock_set = 0
stock_errors = []

# Get default stock location
stock_locs = execute('stock.location', 'search', [[['usage', '=', 'internal']]], {'limit': 1})
if not stock_locs:
    print("  ⚠️ No stock location found, skipping stock quantities")
else:
    stock_loc_id = stock_locs[0]
    
    for r in csv_rows:
        qty_str = r.get('Quantity On Hand', '0').strip()
        if not qty_str or qty_str == '0':
            continue
        
        sku = r['Internal Reference'].strip()
        try:
            prod_ids = execute('product.product', 'search', [[['default_code', '=', sku]]])
            if not prod_ids:
                continue
            
            qty = float(qty_str)
            product_id = prod_ids[0]
            
            # Odoo 13: Use stock.quant to set inventory
            # First check if quant exists
            quant_ids = execute('stock.quant', 'search', [[
                ['product_id', '=', product_id],
                ['location_id', '=', stock_loc_id],
            ]])
            
            if quant_ids:
                # Update existing quant
                execute('stock.quant', 'write', [quant_ids, {'inventory_quantity': qty}])
                execute('stock.quant', 'action_apply_inventory', [quant_ids])
            else:
                # Create new quant
                execute('stock.quant', 'create', [{
                    'product_id': product_id,
                    'location_id': stock_loc_id,
                    'inventory_quantity': qty,
                }])
                # Apply it
                new_quant = execute('stock.quant', 'search', [[
                    ['product_id', '=', product_id],
                    ['location_id', '=', stock_loc_id],
                ]])
                if new_quant:
                    execute('stock.quant', 'action_apply_inventory', [new_quant])
            
            stock_set += 1
            if stock_set % 200 == 0:
                print(f"  ⏳ Stock set: {stock_set}")
        except Exception as e:
            stock_errors.append(f"{sku}: {e}")

# === SUMMARY ===
print(f"\n{'='*50}")
print(f"✅ IMPORT COMPLETE")
print(f"{'='*50}")
print(f"  Products created:  {created}")
print(f"  Skipped (exists):  {skipped}")
print(f"  Stock set:         {stock_set}")
print(f"  Product errors:    {len(errors)}")
print(f"  Stock errors:      {len(stock_errors)}")

if errors:
    print(f"\n⚠️  First 10 product errors:")
    for e in errors[:10]:
        print(f"  {e}")
if stock_errors:
    print(f"\n⚠️  First 10 stock errors:")
    for e in stock_errors[:10]:
        print(f"  {e}")

print(f"\n🔗 Check: {ODOO_URL}/web#action=401")
