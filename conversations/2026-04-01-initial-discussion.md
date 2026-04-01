# Conversation Log - 2026-04-01

## Topic: ERP System Setup

### User's Questions & Our Discussion

**Q1: Can Odoo CE 16 do warehouse + barcode + BigSeller?**
- Warehouse: ✅ Full support (multi-warehouse, locations, lot/serial tracking)
- Barcode: ⚠️ CE doesn't have native barcode app (Enterprise only). Workarounds: keyboard wedge scanners, OCA community modules, or custom module
- BigSeller: ⚠️ No native connector. Need custom API bridge service (1-2 weeks work)

**Q2: Vision for multi-company tracking**
- Company A: Sewing Machine Business (inventory, sales, purchases)
- Company B: Banking (transaction recording, reconciliation)
- Full AP/AR tracking with aging reports
- Bank statement import (OFX/CSV/CAMT)
- Financial reports (P&L, Balance Sheet, Cash Flow)

**Q3: How to save progress**
- User wants to:
  - Save everything in markdown files
  - Push to GitHub with PAT
  - Laptop as server
  - Conversation history preserved

### Key Takeaways
- Odoo CE 16 covers ~80% of needs out of the box
- BigSeller integration is the biggest custom work item
- Barcode in CE needs workaround or custom module
- Multi-company accounting is a core Odoo strength

### Open Questions for User
1. Country (for chart of accounts template)
2. Currency setup
3. Fresh start or migrate existing books?
4. Deployment preference (Docker vs bare metal)
5. GitHub repo details
