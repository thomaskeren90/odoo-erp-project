# Shopee → Odoo 13 Bridge

Syncs Shopee marketplace data directly into Odoo 13 accounting.

## Why Direct (Not BigSeller)?

BigSeller has no public API. This bridge connects **Shopee Open Platform API → Odoo 13 XML-RPC** directly. You can still use BigSeller for multi-platform management, but accounting stays in Odoo.

## What It Syncs

| Shopee Event | Odoo Entry | Account |
|---|---|---|
| Order completed | Customer Invoice (out_invoice) | 410001 E-commerce Sales |
| Payment received | Journal Entry | 111006 SeaBank ↔ 112002 Piutang Marketplace |
| Platform fees | Journal Entry | 611004 Marketplace Fees |
| Returns/refunds | Journal Entry | 510004 Retur & Refund |

## Setup

### 1. Register Shopee App
Go to https://open.shopee.com/developer → Create App → Get partner_id + partner_key

### 2. Configure
Edit `config.py`:
```python
SHOPEE_PARTNER_ID = "your_id"
SHOPEE_PARTNER_KEY = "your_key"
```

### 3. Authorize Your Shop
```bash
python3 app.py --auth
# Opens authorization URL → login → redirect with code
python3 app.py --token <CODE> <SHOP_ID>
```

### 4. Test Connections
```bash
python3 app.py --test
```

### 5. Run Sync
```bash
# One-shot (last 7 days)
python3 app.py

# Last 30 days
python3 app.py --days 30

# Daemon mode (every 30 min)
python3 app.py --daemon
```

## Files

| File | Purpose |
|---|---|
| `config.py` | All configuration (API keys, Odoo creds, account mapping) |
| `shopee_client.py` | Shopee API v2 client (auth, orders, payments, returns) |
| `odoo_client.py` | Odoo 13 XML-RPC client (invoices, journal entries) |
| `app.py` | Main sync engine |
| `sync_state.json` | Tracks what's been synced (auto-created) |
| `shopee_tokens.json` | Auth tokens (auto-created after --token) |

## Account Flow

```
Customer buys on Shopee
        ↓
  Invoice created (410001 Sales + 112002 Piutang Marketplace)
        ↓
  Shopee deducts fees (611004 Marketplace Fee)
        ↓
  Shopee pays out to SeaBank (111006 ↔ 112002)
```
