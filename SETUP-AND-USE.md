# Odoo ERP Project

Integration tools for Odoo 13 — invoice extraction, automation, and posting.

## 🧾 Invoice-to-Odoo Bot

Send a photo of an invoice/receipt to a Telegram bot → AI extracts data → posts to Odoo 13.

### Architecture

```
📱 Phone                        💻 HP Laptop (Docker)
┌───────────────┐              ┌─────────────────────────┐
│ Take photo    │──Telegram───▶│ Telegram Bot            │
│ Send "invoice"│              │   ↓                     │
│               │◀──confirm───│ Ollama (moondream)      │
│               │              │   ↓                     │
│               │              │ Odoo 13 (XML-RPC)       │
│               │              │   ├→ Account Payable    │
│               │              │   ├→ Inventory          │
│               │              │   └→ Expenses           │
└───────────────┘              └─────────────────────────┘
```

### Prerequisites (Docker containers running)

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `odoo13` | odoo:13.0 | 8069 | ERP system |
| `odoo13-db` | postgres:13 | 5432 | Database |
| `ollama_brain` | ollama/ollama:latest | 11434 | Vision AI |
| `n8n_matrix` | n8nio/n8n | 5678 | Automation (optional) |

### Quick Start

```bash
# 1. Clone
git clone https://github.com/thomaskeren90/odoo-erp-project.git
cd odoo-erp-project/invoice-to-odoo

# 2. Install
sudo apt install python3.12-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
nano .env
# Set: TELEGRAM_TOKEN, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD

# 4. Run
python bot.py
```

### Bot Commands

| Command | Action |
|---------|--------|
| `/start` | Welcome + button menu |
| `invoice` | Record as vendor bill (AP + inventory) |
| `expense` | Record as expense entry |
| `receipt` | Record as receipt (bill + expense) |
| `status` | Check Ollama & Odoo connections |
| `/help` | Show help |

### How It Works

1. **Photo** — User sends invoice/receipt photo to Telegram bot
2. **Extract** — Ollama vision model (moondream) reads the image, outputs structured JSON
3. **Post** — Python script connects to Odoo 13 via XML-RPC:
   - Finds or creates supplier partner
   - Creates vendor bill → Accounts Payable
   - Creates inventory receipt (if line items found)
   - Creates expense journal entry
4. **Confirm** — Bot replies with created record IDs

### Project Structure

```
invoice-to-odoo/
├── bot.py              # Telegram bot (main entry point)
├── extract.py          # Ollama vision → JSON extraction
├── post_odoo.py        # Odoo 13 XML-RPC posting
├── run.py              # Folder watcher (alternative to bot)
├── .env.example        # Config template
├── .env                # Config (git-ignored)
├── requirements.txt    # Python dependencies
└── README.md           # Detailed docs
```

### Ollama Models

| Model | Size | Quality | Recommendation |
|-------|------|---------|----------------|
| `moondream` | ~1.7GB | Good | ✅ Currently using |
| `llava` | ~4GB | Better | Recommended upgrade |
| `llava:13b` | ~8GB | Best | If you have RAM |

Pull a different model:
```bash
docker exec ollama_brain ollama pull llava
```

Then update `OLLAMA_MODEL=llava` in `.env`.

### Odoo Account Codes

Adjust in `.env` to match your chart of accounts:

| Variable | Default | Maps to |
|----------|---------|---------|
| `ODOO_EXPENSE_ACCOUNT` | 211000 | Expense account |
| `ODOO_PAYABLE_ACCOUNT` | 200000 | Accounts Payable |
| `ODOO_RECEIVABLE_ACCOUNT` | 120000 | Accounts Receivable |

### Troubleshooting

| Issue | Fix |
|-------|-----|
| Bot won't start | Check `TELEGRAM_TOKEN` in `.env` |
| Extraction fails | Check Ollama: `docker ps \| grep ollama` |
| Odoo auth error | Check `ODOO_DB`, `ODOO_USERNAME`, `ODOO_PASSWORD` |
| Wrong data extracted | Switch to `llava` model |
| Python venv error | `sudo apt install python3.12-venv` |

---

**GitHub:** [thomaskeren90/odoo-erp-project](https://github.com/thomaskeren90/odoo-erp-project)
