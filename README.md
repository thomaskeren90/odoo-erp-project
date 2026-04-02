# Odoo ERP Project

## Vision
Build a multi-company ERP system using Odoo Community Edition 16.

## Companies to Track
1. **Sewing Machine Business** — inventory, sales, purchases, BigSeller e-commerce sync
2. **Banking / Investment** — bank transaction recording, reconciliation, cash flow tracking

## Core Requirements
- Multi-company support (switch between companies)
- Accounts Payable (AP) and Accounts Receivable (AR)
- Bank statement import (OFX/CSV/CAMT)
- Bank reconciliation
- Aging reports (30/60/90/120+ days)
- Warehouse management with barcode scanning
- BigSeller integration (orders, stock sync)
- Financial reports (P&L, Balance Sheet, Cash Flow, Trial Balance)

## Decisions Made
- **Country:** Indonesia
- **Currency:** IDR (Indonesian Rupiah)
- **Books:** Fresh start (no migration needed)
- **Deployment:** Docker (pending confirmation, defaulting to this)
- **GitHub:** https://github.com/thomaskeren90/odoo-erp-project

## Switching Laptops

Everything is in GitHub. To move to a new laptop:

### On Old Laptop
```bash
./backup.sh backup
# Copy the .tar.gz file to new laptop (USB, Google Drive, etc.)
```

### On New Laptop
```bash
git clone https://github.com/thomaskeren90/odoo-erp-project.git
cd odoo-erp-project
docker-compose up -d
# Wait 30 seconds, then:
./backup.sh restore odoo_full_backup_TIMESTAMP.tar.gz
```

All data, settings, invoices, inventory — everything follows you.


## Chart of Accounts

Custom module: `addons/custom_coa/`

### Banks (1110xx)
- 111001 - Bank BCA
- 111002 - Bank Mandiri
- 111003 - Bank BNI
- 111004 - Bank BRI
- 111005 - Bank CIMB Niaga

### Inventory (1120xx)
- 112001 - Persediaan Barang

### Sales (4100xx)
- 410001 - Pendapatan Penjualan Produk
- 410002 - Pendapatan Jasa

### Purchase/COGS (5100xx)
- 510001 - Harga Pokok Penjualan
- 510002 - Pembelian Barang

### Expenses - Toko (6110xx)
- 611001-611004 - Sewa, Listrik, Operasional, Gaji

### Expenses - Pribadi (6120xx)
- 612001-612003 - Hidup, Transportasi, Lainnya

### Expenses - Kos (6130xx)
- 613001-613004 - Sewa, Listrik, Air, Perawatan

## Decisions Pending
- [ ] Need external access (domain + HTTPS)?

## Phases
### Phase 1: Core Accounting (Week 1)
- Set up Odoo CE 16
- Configure both companies
- Chart of accounts, journals, opening balances
- Bank statement import workflow

### Phase 2: Inventory & E-commerce (Week 2-3)
- Warehouse setup
- Barcode module (custom or OCA community)
- BigSeller API bridge

### Phase 3: Polish (Week 4+)
- Custom reports
- Automation & workflows
- Additional integrations
