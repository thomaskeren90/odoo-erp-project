# 2026-04-12 — Receipt Automation Pipeline

**Date:** Sunday, April 12, 2026
**Host:** kusum
**Duration:** ~50 min (22:03 - 22:54)

## Summary

Built receipt automation pipeline (WhatsApp → OCR → CSV → Odoo 13). Connected to Odoo, created COGS account, imported 3 invoices, fixed doubled amounts. WhatsApp bot setup pending.

## What was done

1. **Verified Odoo 13 connection** — XML-RPC, uid 2, 5110 products, 4 partners
2. **Created COGS account** — `50100010 Harga Pokok Penjualan (COGS)`
3. **Built receipt-automation pipeline** (in `receipt-automation/`):
   - `ocr_parser.py` — Ollama Vision OCR for receipt images
   - `csv_to_odoo.py` — CSV batch importer to Odoo (DR Inventory / CR AP)
   - `odoo_pusher.py` — JSON to Odoo journal entries
   - `csv_logger.py` — Audit trail CSV logger
   - `test_pipeline.py` — End-to-end test runner
   - `fix_and_reimport.py` — Fix script for doubled COGS entries
   - `fix_v2.py` — Final fix (handles None returns from action_post)
   - `n8n/workflow.json` — WhatsApp webhook workflow (pending setup)
4. **Imported 3 invoices** into Odoo 13:

| Move ID | Invoice | Supplier | Amount |
|---------|---------|----------|--------|
| 7 | INV/2026/05598 | CV. Aurora Sejahtera | Rp 160,000 |
| 8 | EO 26032 | Toko Makmur Permai | Rp 2,130,000 |
| 9 | AK 81357 | Toko Makmur | Rp 115,000 |

**Total: Rp 2,405,000** — posted as DR Persediaan Barang / CR Hutang Usaha

5. **Fixed doubled COGS entries** — original entries incorrectly debited both Inventory and COGS. Reversed and re-imported with correct 2-line entries.

## Accounts Used

| Code | Name | Role |
|------|------|------|
| 112001 | Persediaan Barang | Inventory (DR) |
| 21100010 | Hutang Usaha | AP (CR) |
| 50100010 | Harga Pokok Penjualan (COGS) | Created today (for future sales) |

## Partners Created

- CV. Aurora Sejahtera (ID: 9)
- Toko Makmur Permai (ID: 10)
- Toko Makmur (ID: 11)

## Docker Stack (on kusum)

| Container | Image | Status |
|-----------|-------|--------|
| odoo13 | odoo:13.0 | ✅ Up (port 8069) |
| odoo13-db | postgres:13 | ✅ Up (5432) |
| ollama_brain | ollama/ollama:latest | ✅ Up (port 11434) |
| n8n_matrix | n8nio/n8n | ✅ Up (port 5678) |

## Lessons Learned

- Odoo 13 `action_post` returns None — must handle xmlrpc Fault for None values
- COGS = expense at SALE time, not purchase time. Purchases: DR Inventory / CR AP
- Account codes in custom Indonesian COA differ from defaults — always verify with `account.account` search
- `button_draft` / `button_cancel` also return None via XML-RPC — use reversal entries instead

## Next Steps

- [ ] Set up WhatsApp Cloud API (Meta Developer Portal on computer browser)
- [ ] Get Phone Number ID + Access Token
- [ ] Expose n8n webhook (ngrok or Cloudflare Tunnel)
- [ ] Import n8n workflow and activate
- [ ] Test full pipeline: photo → WhatsApp → OCR → Odoo
- [ ] Change default password `admin123` to something stronger
- [ ] Clean up old draft/cancelled journal entries (moves 1-6) in Odoo
