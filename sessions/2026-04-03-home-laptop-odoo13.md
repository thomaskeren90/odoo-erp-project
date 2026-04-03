# Session Log: Home Laptop — Odoo 13 CE Setup
**Date:** 2026-04-03
**Machine:** Home Laptop (WSL)
**Goal:** Get accounting working on Odoo 13 CE

## What We Did

### 1. GitHub Connection Fixed
- Old PAT (ghp_CjZW...VNw5N) was expired → 401 error
- Updated remote URL with new PAT
- Verified connection working via `git fetch`

### 2. Version Migration: Odoo 17 → 16 → 13
- Previously ran Odoo 17, then Odoo 16
- Switched to Odoo 13 CE on home laptop
- Docker containers: `odoo13` (odoo:13.0) + `odoo13-db` (postgres:13)
- Updated all GitHub files to match Odoo 13

### 3. GitHub Cleanup
- Deleted old Odoo 16/17 conversation logs
- Updated README, SETUP-GUIDE, docker-compose.yml, backup.sh
- Removed old docker-compose.yml and odoo.conf from GitHub
- User pushed authentic Odoo 13 config from home laptop

### 4. Custom Chart of Accounts Module — Updated for Odoo 13
- Rewrote `addons/custom_coa/` for Odoo 13 data model
- Key changes from Odoo 16:
  - `account_type` (selection) → `user_type_id` (many2one)
  - `default_account_id` → `default_debit_account_id` / `default_credit_account_id`
  - Version: 13.0.1.0.0

### 5. Bank Accounts (5 total)
| Code | Account | Journal | Purpose |
|------|---------|---------|---------|
| 111001 | BCA 1 Prvt | BCA1 | Personal |
| 111002 | BCA 2 Thomas Susin Chen (Toko) | BCA2 | Shop (5300138677) |
| 111003 | BCA Expressi | BCAX | Expressi |
| 111004 | Bank SAQU | SAQU | — |
| 111005 | Superbank | SUPB | — |

### 6. OCA Bank Reconciliation (Free)
- Installed OCA modules for free bank reconciliation:
  - `account_mass_reconcile`
  - `account_bank_statement_import`
  - `account_bank_statement_import_ofx`
  - `account_bank_statement_import_txt_xlsx`
- Workaround for Odoo CE missing Enterprise bank reconciliation feature

### 7. Issue: Accounting Upgrade Prompt
- Odoo 13 CE shows "Upgrade" prompt for full accounting features
- Free features: Chart of Accounts, Journal Entries, Invoices, Bills, Payments
- Locked features: Bank Reconciliation widget, Bank statement import (native)
- Solution: OCA modules above

## Pending
- [ ] Install/upgrade custom_coa module in Odoo 13
- [ ] Verify 5 bank accounts appear in Chart of Accounts
- [ ] Import OCA bank statement modules
- [ ] Test bank reconciliation workflow
- [ ] Set up opening balances
