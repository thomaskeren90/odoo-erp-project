# Session: 2026-04-03 — Receipt Scanner (Phone Capture)

## Date
2026-04-03 17:15 - 18:08 (GMT+8)

## Context
- User: thomaskeren90 (tomhack)
- Odoo 13 running in Docker on WSL
- DB: tokoodoo13 | User: tokomakmur | Port: 8069
- Postgres: odoo13-db (user: odoo13, pass: odoo13)
- Also running: Ollama (11434), n8n (5678)

## What We Did

### 1. GitHub Access
- Connected to GitHub via API with PAT
- Found repo: `thomaskeren90/odoo-erp-project` (private)
- Updated git remote URL with new token with `repo` scope

### 2. Odoo 13 Connection
- Found database: tokoodoo13
- Admin user: tokomakmur (uid: 2, is_admin: true)
- Reset password to admin123 via psql
- Confirmed XML-RPC auth works

### 3. Receipt Scanner App
- Built Flask web app for phone-based receipt scanning
- Features:
  - 📸 Phone camera capture (mobile-friendly UI)
  - 🔍 OCR via Tesseract (Indonesian + English)
  - 📋 Choose: Expense (biaya) or COGS (inventory/stok)
  - ✅ Creates vendor bill in Odoo 13 via XML-RPC
  - 📎 Attaches receipt image to the record
- Files:
  - `app.py` — Flask web app
  - `config.py` — Odoo connection config
- Running on: http://172.26.194.224:5000

## Dependencies Installed
- tesseract-ocr, tesseract-ocr-ind
- flask, pillow, pytesseract (pip3 --break-system-packages)

## Notes
- Odoo 13 API uses xmlrpc/2/common and xmlrpc/2/object
- account.move type='in_invoice' for vendor bills
- Products marked purchase_ok=True for COGS
- User's company currency: Rp (Rupiah)
