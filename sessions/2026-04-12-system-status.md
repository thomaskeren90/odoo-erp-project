# 2026-04-12 — Receipt Automation Pipeline

**Date:** Sunday, April 12, 2026
**Host:** kusum
**Duration:** ~30 min

## Summary

Built WhatsApp→OCR→CSV→Odoo13 receipt automation pipeline. Successfully imported 3 invoices into Odoo 13.

## What was done

1. **Verified Odoo 13 connection** — XML-RPC, uid 2, 5110 products, 4 partners
2. **Created COGS account** — `50100010 Harga Pokok Penjualan (COGS)` in Odoo
3. **Built receipt-automation pipeline** (pushed to repo):
   - `ocr_parser.py` — Ollama Vision OCR for receipt images
   - `csv_to_odoo.py` — CSV batch importer to Odoo
   - `odoo_pusher.py` — JSON to Odoo journal entries
   - `csv_logger.py` — Audit trail CSV logger
   - `test_pipeline.py` — End-to-end test runner
   - `n8n/workflow.json` — WhatsApp webhook workflow
4. **Imported 3 invoices** into Odoo 13:

| Move ID | Invoice | Supplier | Amount |
|---------|---------|----------|--------|
| 1 | INV/2026/05598 | CV. Aurora Sejahtera | Rp 160,000 |
| 2 | EO 26032 | Toko Makmur Permai | Rp 2,130,000 |
| 3 | AK 81357 | Toko Makmur | Rp 115,000 |

**Total: Rp 2,405,000** — all as COGS entries (DR Inventory + DR COGS / CR AP)

## Accounts Used

| Code | Name | Role |
|------|------|------|
| 112001 | Persediaan Barang | Inventory (DR) |
| 21100010 | Hutang Usaha | AP (CR) |
| 50100010 | Harga Pokok Penjualan (COGS) | COGS (DR) — created today |

## Partners Created

- CV. Aurora Sejahtera (ID: 9)
- Toko Makmur Permai (ID: 10)
- Toko Makmur (ID: 11)

## Docker Stack (on kusum)

| Container | Image | Status |
|-----------|-------|--------|
| odoo13 | odoo:13.0 | ✅ Up |
| odoo13-db | postgres:13 | ✅ Up |
| ollama_brain | ollama/ollama:latest | ✅ Up |
| n8n_matrix | n8nio/n8n | ✅ Up |

## Next Steps

- [ ] Set up WhatsApp Cloud API (Meta Developer portal)
- [ ] Import n8n workflow and test WhatsApp trigger
- [ ] Test OCR with actual receipt photos (need llava model on Ollama)
- [ ] Change default password `admin123` to something stronger
- [ ] Create dedicated bot user with limited permissions
