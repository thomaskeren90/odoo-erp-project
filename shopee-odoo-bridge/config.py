"""
Shopee-to-Odoo Bridge Configuration
=====================================
Register at https://open.shopee.com/developer to get your API credentials.
Shopee requires: partner_id, partner_key, shop_id

After registration:
1. Create an app at open.shopee.com
2. Get partner_id + partner_key
3. Authorize your shop → get shop_id + refresh token
4. Fill in the values below
"""

# ============================================
# SHOPEE API CONFIG
# ============================================
SHOPEE_PARTNER_ID = ""        # e.g. 123456
SHOPEE_PARTNER_KEY = ""       # your partner key (secret)
SHOPEE_SHOP_ID = ""           # your shop ID after auth
SHOPEE_REGION = "ID"          # ID = Indonesia
SHOPEE_BASE_URL = "https://partner.shopeemobile.com"  # production

# Token storage (auto-managed after first auth)
SHOPEE_TOKEN_FILE = "shopee_tokens.json"

# ============================================
# ODOO 13 CONFIG
# ============================================
ODOO_URL = "http://localhost:8069"
ODOO_DB = "tokoodoo13"
ODOO_USERNAME = "tokomakmur"
ODOO_PASSWORD = "admin123"

# ============================================
# ACCOUNT MAPPING (matches custom_coa module)
# ============================================
ACCOUNT_MAP = {
    # Revenue
    "ecommerce_sales": "410001",      # Penjualan Produk E-commerce
    "marketplace_fee": "611004",      # Beban Komisi Marketplace
    "logistics": "510003",            # Biaya Logistik & Pengiriman
    "returns_refund": "510004",       # Retur & Refund
    "packing": "611005",              # Beban Packing & Lakban

    # Bank
    "seabank": "111006",              # SeaBank Shopee

    # AR/AP
    "ar_marketplace": "112002",       # Piutang Marketplace
    "inventory": "113001",            # Persediaan Barang
    "cogs": "510001",                 # HPP
}

# Journal mapping
JOURNAL_MAP = {
    "seabank": "SEAB",
    "sales": "SALES",
    "purchase": "PURCH",
    "expense": "EXP",
}

# ============================================
# SYNC SETTINGS
# ============================================
SYNC_INTERVAL_MINUTES = 30    # how often to sync
ORDER_STATUS_SYNC = ["COMPLETED", "PROCESSED", "READY_TO_SHIP"]
CURRENCY = "IDR"
