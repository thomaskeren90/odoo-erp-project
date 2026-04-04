# Session Log — 2026-04-04 (2)

## Task: Full COA Rebuild — Indonesian Standard 1xxx-6xxx

**Date:** 2026-04-04 20:35 (GMT+8)
**Context:** User has multiple businesses — e-commerce (sewing machines via Shopee), mesin jahit rental, kos, car rental. Shifting focus to e-commerce factory.

## What We Did

### Replaced entire COA module (v13.0.1.0.0 → v13.0.2.0.0)

Old COA had 5 banks + 20 accounts (toko/personal/kos splits).
New COA follows Indonesian standard structure with 32 accounts across 6 categories.

### Accounts (32 total)

| Section | Accounts |
|---------|----------|
| Assets 1xxx | 6 banks, AR (general + marketplace), inventory, 2 prepayments, 2 fixed assets, accum depreciation |
| Liabilities 2xxx | AP, salary payable, PPN tax, customer deposits |
| Equity 3xxx | Capital, prive, retained earnings |
| Revenue 4xxx | E-commerce sales, service, kos rental, car rental, mesin jahit rental, other income |
| COGS 5xxx | HPP, bahan baku/spareparts, logistics, returns/refund |
| Expenses 6xxx | Salary, utilities, rent, marketplace fees, packing, ads, vehicle maint, kos maint, bank admin |

### New accounts added (vs old COA)
- 112001 - Piutang Usaha / AR
- 112002 - Piutang Marketplace (Shopee disbursement tracking)
- 114001 - Uang Muka Supplier
- 114002 - Uang Muka Iklan Platform
- 121001 - Aset Tetap Kendaraan Rental
- 121002 - Aset Tetap Mesin Jahit Industri
- 122001 - Akumulasi Penyusutan
- 211001-214001 - All liability accounts
- 311000-313000 - Equity accounts
- 410005 - Pendapatan Sewa Mesin Jahit
- 510002-510004 - Bahan baku, logistics, returns
- 611005-611006 - Packing, ads
- 612001, 613001, 619001 - Vehicle/kos maintenance, bank admin

### Journals (10 total)
BCA1, BCA2, BCAX, SAQU, SUPB, SEAB (bank) + SALES (sale) + PURCH (purchase) + EXP (general) + CSH (cash)

### Files Changed
- `addons/custom_coa/data/chart_of_accounts.xml` — full rebuild
- `addons/custom_coa/data/journals.xml` — 10 journals
- `addons/custom_coa/__manifest__.py` — v13.0.2.0.0

## Pending
- [ ] Pull + upgrade on home laptop: `docker exec odoo13 odoo ... -u custom_coa --stop-after-init`
- [ ] Verify all 32 accounts in Chart of Accounts
- [ ] Verify all 10 journals
- [ ] Set opening balances
- [ ] Configure Shopee payment flow (order → SeaBank)
