# Session Log: Receipt Scanner Setup
**Date:** 2026-04-06
**Goal:** Get receipt scanner working (AI vision → Odoo 13)

---

## What We Did

### 1. Fixed README
- Repo incorrectly said "Odoo CE 16" — corrected to **Odoo 13 CE**
- Pushed fix to GitHub

### 2. Environment Setup
- Installed Flask, requests, Pillow on laptop
- Created `config.py` (gitignored, not in repo)

**config.py values:**
- Odoo DB: `tokoodoo13`
- Odoo user: `admin`
- Odoo password: `admin123`
- AI Provider: `gemini` (Ollama too slow — 3.7GB RAM, no GPU)
- Gemini API Key: `AIzaSyDT-9K-46GbjfkTf2IuXi4h_824U3wt_A0`

### 3. Gemini Model Issues
- `gemini-1.5-flash` — **deprecated**, doesn't exist anymore
- `gemini-2.0-flash` — **429 quota exceeded** (free tier limit: 0)
- `gemini-2.0-flash-lite` — **429** also exhausted
- ✅ `gemini-2.5-flash` — **works**, has free tier quota
- ✅ `gemini-2.5-flash-lite` — also works

**Current code uses: `gemini-2.5-flash`**

### 4. Upload UI Issues
- Original UI had hidden file input + Camera/Gallery buttons
- **Problem:** Clicking buttons wouldn't trigger file picker reliably
- Changed to visible file input + "Scan Receipt" submit button
- **Still not working:** File can be selected, but pressing Enter/button kicks user out of terminal (Flask debug mode restart issue?)

---

## Current Status: ❌ NOT WORKING

**What works:**
- ✅ Gemini API (text + vision) — tested from sandbox, returns correct data
- ✅ Flask app starts on `localhost:5000`
- ✅ Page loads in browser

**What doesn't work:**
- ❌ Upload → AI extraction → results display
- ❌ Suspected issue: Flask debug mode (`debug=True`) causes restart, or terminal session conflict
- ❌ When user presses submit, terminal session crashes/kicks out

---

## To Debug Next Session

1. **Run without debug mode:**
   ```bash
   # In app.py, change: app.run(host=HOST, port=PORT, debug=False)
   python3 app.py
   ```

2. **Test upload via curl (bypass browser):**
   ```bash
   curl -X POST http://127.0.0.1:5000/scan -F "photo=@/path/to/receipt.jpg" --max-time 120
   ```

3. **Check if it's a Flask debug restart issue:**
   - Debug mode auto-restarts on file changes
   - Maybe config.py write triggers a restart mid-request

4. **Alternative: disable Odoo connection during scan** (if Odoo is down, it might block)

---

## Files Modified
- `README.md` — version fix
- `app.py` — Gemini model update, UI upload fix

## Laptop Specs
- RAM: 3.7GB (2.4GB free)
- No GPU
- Ollama models: qwen3.5:0.8b, gemma3:1b, qwen:0.5b (all too small for vision)
- IP: 172.26.194.224
