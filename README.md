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

## Decisions Pending
- [ ] Country (affects chart of accounts, tax/GST setup)
- [ ] Currency (MYR? SGD? Multi-currency?)
- [ ] Existing books to migrate or fresh start?
- [ ] Deployment: Docker or bare metal on laptop?
- [ ] Domain + HTTPS or localhost?
- [ ] GitHub repo URL for saving progress

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
