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

## Decisions Pending
- [ ] Laptop as server — accessible on local network only?
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
