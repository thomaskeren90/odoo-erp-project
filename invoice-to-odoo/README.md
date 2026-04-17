# Invoice-to-Odoo Bot 🧾

Send a photo of an invoice/receipt to your Telegram bot → it extracts data with AI → posts to Odoo 13.

## Architecture

```
📱 Phone                        💻 HP Laptop
┌───────────────┐              ┌─────────────────────┐
│ Take photo    │──Telegram───▶│ Telegram Bot (run)  │
│ "invoice"     │              │   ↓                 │
│               │◀──confirm───│ Ollama (moondream)  │
│               │              │   ↓                 │
│               │              │ Odoo 13 (XML-RPC)   │
└───────────────┘              └─────────────────────┘
```

## Quick Start

### 1. Prerequisites (already running on your HP)

- ✅ Ollama in Docker (`ollama_brain`) — port 11434
- ✅ Odoo 13 in Docker (`odoo13`) — port 8069
- ✅ moondream model pulled

### 2. Install

```bash
cd invoice-to-odoo

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure

```bash
# .env is already configured with your credentials
# Edit if needed:
nano .env
```

### 4. Run

```bash
# Activate venv
source .venv/bin/activate

# Start the bot
python bot.py
```

The bot will connect to Telegram and start listening.

### 5. Use from your phone

1. Open Telegram, find your bot
2. Send `/start` — get the button menu
3. Tap **📸 Invoice** (or send `invoice`)
4. Send the photo
5. Bot extracts data → posts to Odoo → sends confirmation

## Commands

| Command | What it does |
|---------|-------------|
| `/start` | Welcome + button menu |
| `invoice` | Record as vendor bill (AP + inventory) |
| `expense` | Record as expense entry |
| `receipt` | Record as receipt (bill + expense) |
| `status` | Check Ollama & Odoo connections |
| `/help` | Show help |

## Files

```
invoice-to-odoo/
├── bot.py           ← Telegram bot (main entry)
├── extract.py       ← Ollama vision extraction
├── post_odoo.py     ← Odoo 13 XML-RPC posting
├── run.py           ← Folder watcher (alternative to bot)
├── .env             ← Config (DO NOT COMMIT)
├── .env.example     ← Template
├── requirements.txt
└── README.md
```

## Tips

- **moondream** is lightweight. For better accuracy, pull `llava`:
  ```bash
  docker exec ollama_brain ollama pull llava
  ```
  Then change `OLLAMA_MODEL=llava` in `.env`
- Phone needs internet → bot needs internet → laptop needs to be on
- Processed images go to `processed/` folder, failed ones to `failed/`

## Odoo Account Codes

Adjust in `.env` to match YOUR chart of accounts:

| Variable | Default | What it maps to |
|----------|---------|----------------|
| `ODOO_EXPENSE_ACCOUNT` | 211000 | Expense account |
| `ODOO_PAYABLE_ACCOUNT` | 200000 | Accounts Payable |
| `ODOO_RECEIVABLE_ACCOUNT` | 120000 | Accounts Receivable |

## Troubleshooting

**Bot won't start** → Check `TELEGRAM_TOKEN` in `.env`

**Extraction fails** → Is Ollama running? `docker ps | grep ollama`

**Odoo errors** → Run `python post_odoo.py` to test connection

**Wrong data extracted** → Try `llava` instead of `moondream`
