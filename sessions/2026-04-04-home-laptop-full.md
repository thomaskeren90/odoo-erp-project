# Session Log: Home Laptop — 2026-04-04 20:21-20:51 (GMT+8)

**Machine:** Home Laptop (WSL + zsh + Docker)
**Containers:** odoo13, odoo13-db, ollama_brain, n8n_matrix
**Database:** tokoodoo13 | User: tokomakmur | Port: 8069

## What We Did

### 1. Added SeaBank (Shopee) to COA
- Account 111006 — SeaBank (Shopee), journal code SEAB
- Pushed to GitHub, upgraded custom_coa module via CLI
- `docker exec odoo13 odoo ... -u custom_coa --stop-after-init`

### 2. Full COA Rebuild — Indonesian Standard 1xxx-6xxx
- Replaced old COA (5 banks + 20 accounts) with Indonesian standard structure
- New COA: 32 accounts across 6 categories + 10 journals
- Module bumped to v13.0.2.0.0

#### Accounts (32 total)

| Code | Account | Type |
|------|---------|------|
| 111001 | BCA 1 Prvt | Bank |
| 111002 | BCA 2 Thomas Toko | Bank |
| 111003 | BCA Expressi | Bank |
| 111004 | Bank SAQU | Bank |
| 111005 | Superbank | Bank |
| 111006 | SeaBank Shopee | Bank |
| 112001 | Piutang Usaha / AR | AR |
| 112002 | Piutang Marketplace | AR |
| 113001 | Persediaan Barang | Inventory |
| 114001 | Uang Muka Supplier | Prepayment |
| 114002 | Uang Muka Iklan Platform | Prepayment |
| 121001 | Aset Tetap - Kendaraan Rental | Fixed Asset |
| 121002 | Aset Tetap - Mesin Jahit Industri | Fixed Asset |
| 122001 | Akumulasi Penyusutan Aset | Fixed Asset |
| 211001 | Hutang Usaha / AP | AP |
| 212001 | Hutang Gaji Karyawan | Liability |
| 213001 | Hutang Pajak PPN | Liability |
| 214001 | Uang Muka Pelanggan / Deposit | Liability |
| 311000 | Modal Disetor / Capital | Equity |
| 312000 | Prive / Owner Drawing | Equity |
| 313000 | Saldo Laba / Retained Earnings | Equity |
| 410001 | Penjualan Produk E-commerce | Revenue |
| 410002 | Pendapatan Jasa Service | Revenue |
| 410003 | Pendapatan Sewa Kos | Revenue |
| 410004 | Pendapatan Sewa Mobil | Revenue |
| 410005 | Pendapatan Sewa Mesin Jahit | Revenue |
| 420001 | Pendapatan Lain-lain | Revenue |
| 510001 | Harga Pokok Penjualan / HPP | COGS |
| 510002 | Biaya Bahan Baku / Spareparts | COGS |
| 510003 | Biaya Logistik & Pengiriman | COGS |
| 510004 | Retur & Refund | COGS |
| 611001 | Beban Gaji & Tunjangan | Expense |
| 611002 | Beban Listrik, Air & WiFi | Expense |
| 611003 | Beban Sewa Gudang/Kantor | Expense |
| 611004 | Beban Komisi Marketplace / BigSeller | Expense |
| 611005 | Beban Packing & Lakban | Expense |
| 611006 | Beban Iklan & Promosi | Expense |
| 612001 | Beban Perawatan Kendaraan Rental | Expense |
| 613001 | Beban Perawatan Gedung Kos | Expense |
| 619001 | Beban Administrasi Bank | Expense |

#### Journals (10 total)
BCA1, BCA2, BCAX, SAQU, SUPB, SEAB (bank) + SALES (sale) + PURCH (purchase) + EXP (general) + CSH (cash)

### 3. Shopee-to-Odoo Bridge Created
- Built API bridge in `shopee-odoo-bridge/`
- Connects Shopee Open Platform API → Odoo 13 XML-RPC directly
- Skips BigSeller (no public API)
- Zero external dependencies (Python stdlib only)

#### Bridge Files
| File | Purpose |
|------|---------|
| config.py | Shopee API keys, Odoo creds, account mapping |
| shopee_client.py | Shopee API v2 (auth, orders, wallet, returns) |
| odoo_client.py | Odoo 13 XML-RPC client |
| app.py | Main sync engine (one-shot, daemon, auth) |
| README.md | Documentation |

#### Sync Flow
- Order → Customer Invoice (410001 E-commerce Sales + 112002 Piutang Marketplace)
- Disbursement → SeaBank Journal Entry (111006 ↔ 112002)
- Fees → Marketplace Fee (611004)
- Returns → Retur & Refund (510004)

### 4. Business Context
- User has multiple businesses: e-commerce (sewing machines via Shopee), mesin jahit rental, kos, car rental
- Focus shifting to e-commerce factory
- Shopee payments go to SeaBank
- Uses BigSeller for multi-platform management (but no API available)

## Pending
- [ ] Register at https://open.shopee.com/developer → get partner_id + partner_key
- [ ] Fill in config.py with Shopee credentials
- [ ] Run `python3 app.py --auth` → authorize shop
- [ ] Test connections: `python3 app.py --test`
- [ ] First sync: `python3 app.py --days 30`
- [ ] Set opening balances in Odoo
- [ ] Revoke old GitHub PAT (shared in plain text)
