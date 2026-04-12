# Receipt Automation Pipeline

**WhatsApp → OCR → CSV → Odoo 13**

## Architecture

```
📱 WhatsApp Photo
      │
      ▼
  n8n Webhook (WhatsApp Cloud API trigger)
      │
      ▼
  🤖 Ollama Vision OCR (llava)
      │
      ▼
  📄 JSON: {vendor, date, amount, line_items}
      │
      ▼
  ❓ Bot asks: "COGS or Expense?"
      │
      ├─ Expense ──→ 1 journal entry (DR Expense / CR Bank)
      │
      └─ COGS ──→ 3 entries (DR Inventory + DR COGS / CR AP)
      │
      ▼
  📋 CSV log (audit trail)
```

## Quick Start (on kusum)

```bash
# 1. Test Odoo connection
python3 scripts/odoo_pusher.py  # (edit creds first or use .env)

# 2. Test OCR on a receipt image
python3 scripts/ocr_parser.py samples/test-receipt.jpg

# 3. Full pipeline test
python3 scripts/test_pipeline.py samples/test-receipt.jpg expense
```

## Files

| File | Purpose |
|------|---------|
| `scripts/ocr_parser.py` | Ollama Vision OCR → structured JSON |
| `scripts/odoo_pusher.py` | JSON → Odoo 13 journal entries |
| `scripts/csv_logger.py` | Append to daily CSV audit log |
| `scripts/test_pipeline.py` | End-to-end test runner |
| `n8n/workflow.json` | Import into n8n for WhatsApp automation |
| `.env.example` | Copy to `.env` and fill in creds |
| `logs/` | Daily CSV receipt logs |

## Chart of Accounts (default)

| Account | Code | Use |
|---------|------|-----|
| Inventory | 101000 | DR for COGS |
| Bank | 101200 | CR for Expense |
| AP Trade | 211100 | CR for COGS |
| COGS | 501000 | DR for COGS |
| Operating Expenses | 611000 | DR for Expense |

**Adjust these codes to match your actual COA in Odoo.**

## n8n Setup

1. Import `n8n/workflow.json` into n8n at http://localhost:5678
2. Configure WhatsApp Cloud API credentials in n8n
3. Update webhook URL in Meta Developer portal
4. Activate workflow
