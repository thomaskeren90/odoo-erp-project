# Session Log — 2026-04-05

## Task: Product Data Cleanup, Odoo Import & Warehouse Shelving Plan

**Date:** 2026-04-05 16:43-17:39 (GMT+8)
**Machine:** Remote (webchat)
**User:** thomaskeren90

## Context

User has an Odoo 13 CE instance running in Docker (odoo13 container, postgres:13, DB: tokoodoo13). They sell sewing machine parts and accessories via Shopee, managed through BigSeller. The challenge: 5,000+ product rows across multiple BigSeller/Shopee exports, with variations making SKU management messy.

## What We Did

### 1. GitHub Access & Repo Review
- Accessed `thomaskeren90/odoo-erp-project` (private repo)
- Reviewed all 7 session files from April 3-4
- Identified current state: Odoo 13 CE, custom COA (32 accounts, 10 journals), Shopee bridge built but awaiting API credentials

### 2. BigSeller/Shopee Data Analysis
- Analyzed original BigSeller export (bigseller2programtkpush): 3,548 rows, 1,894 unique SKUs
- Analyzed two Shopee direct exports: 5,008 + 98 rows
- Merged and deduplicated: **5,106 product variants across 2,637 unique Shopee products**
- Identified variation complexity: 1-20+ variations per product
- Price range: Rp 450 - Rp 85,000,000

### 3. Data Cleanup & Odoo Import Preparation
- Extracted categories from product name prefixes → consolidated to **22 clean categories**
- Generated internal SKUs: `TKM-00001` to `TKM-5106`
- Generated internal barcodes (CODE128 format) for 5,103 items without EAN13
- Created Odoo 13 CE compatible CSV import file

**Top categories:**
- Mesin Jahit / Sewing Machine: 2,156
- Jarum / Needles: 1,147
- Mesin Obras / Overlock: 339
- Mesin / Machines: 284
- Gunting / Scissors: 180
- Sparepart / Parts: 160

### 4. ABC Velocity Analysis
- A-class (top 80% volume): 146 items
- B-class (next 15%): 288 items
- C-class (last 5%): 4,540 items

### 5. Warehouse Shelving Plan
Designed 3-zone warehouse layout:

| Zone | Name | Type | Shelves | Items |
|------|------|------|---------|-------|
| A | Small Parts Wall | Bins + Pegboard | 39 | 1,606 |
| B | Medium Parts | Standard Shelving | 9 | 415 |
| C | Large / Machines | Heavy Duty + Floor | 216 | 3,085 |

- Generated shelf location codes: A-01 through C-216
- Assigned every product to a shelf location
- Created printable shelf labels (HTML with barcodes)
- Created Odoo 13 warehouse locations import file

### 6. Files Pushed to GitHub
- `import/odoo13_product_import_final.csv` — 5,106 products for Odoo import
- `import/shelving_plan_full.csv` — Every item → shelf location
- `import/shelf_labels.csv` — 264 shelf labels with barcodes
- `import/shelf_labels_print.html` — Printable shelf labels
- `import/odoo13_locations_import.csv` — Odoo warehouse locations
- `import/import_to_odoo.py` — XML-RPC import script

### 7. Git Remote Fix
- User's remote URL had expired PAT token (ghp_1K9a...)
- Recommended switching to SSH: `git remote set-url origin git@github.com:thomaskeren90/odoo-erp-project.git`

## Pending
- [ ] Import products into Odoo 13 (web UI or script)
- [ ] Import warehouse locations into Odoo 13
- [ ] Print shelf labels from shelf_labels_print.html
- [ ] Physically label shelves and stock items
- [ ] Set cost prices (currently 0 for all products)
- [ ] Register for Shopee Open Platform API
- [ ] Rotate GitHub PAT (old token exposed in chat)
- [ ] Connect Shopee bridge once API credentials obtained
