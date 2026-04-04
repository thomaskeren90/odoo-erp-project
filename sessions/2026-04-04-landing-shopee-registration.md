# Session Log: Home Laptop — 2026-04-04 20:49-21:15 (GMT+8)

**Machine:** Home Laptop (WSL + zsh + Docker)
**Company:** PT Golden Crystal Candy
**Address:** Jl Perniagaan Raya No. 12, Jakarta Barat 11230

## What We Did

### 1. Shopee Developer Registration — Landing Page
- Built professional landing page for Shopee Open Platform application
- Registered as Third Party Partner Platform (not direct seller)
- Public repo created: `thomaskeren90/shopee-odoo-bridge`
- GitHub Pages enabled: https://thomaskeren90.github.io/shopee-odoo-bridge/

### 2. Landing Page Features
- Hero section with company branding and animated dashboard preview
- Vision & Mission section (PT Golden Crystal Candy as system integrator)
- 6 service cards: Marketplace Integration, ERP Implementation, Bank Reconciliation, Inventory Management, Financial Reporting, Process Automation
- Integration flow diagram: Shopee → Invoice → Fees → SeaBank → Reports
- Company address with Google Maps embed
- Demo login section (credentials: demo / demo123)
- Responsive design, scroll animations, dark theme

### 3. Demo Login
- Built-in demo dashboard on main page (no separate demo.html)
- Test credentials: demo / demo123
- Shows sync status JSON on login (shop, db, accounts, orders, SeaBank balance)
- Removed standalone demo.html — login now inline on main page

### 4. Key URLs
- Product URL for Shopee: https://thomaskeren90.github.io/shopee-odoo-bridge/
- Private code repo: https://github.com/thomaskeren90/odoo-erp-project (NOT linked on landing page)
- Public landing repo: https://github.com/thomaskeren90/shopee-odoo-bridge

### 5. Security Note
- Private repo (odoo-erp-project) NOT referenced on landing page
- Landing page is separate public repo — Shopee reviewers only see company/product info
- No sensitive data exposed on public site

## Shopee Developer Registration Values
- Product URL: https://thomaskeren90.github.io/shopee-odoo-bridge/
- Live Test Username: demo
- Live Test Password: demo123

## Pending
- [ ] Complete Shopee developer registration at https://open.shopee.com/developer
- [ ] Get partner_id + partner_key from Shopee
- [ ] Fill in config.py with Shopee credentials
- [ ] Run `python3 app.py --auth` → authorize shop
- [ ] First sync: `python3 app.py --days 30`
- [ ] Set opening balances in Odoo
- [ ] Revoke old GitHub PAT (shared in plain text during session)
