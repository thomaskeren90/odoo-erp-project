#!/usr/bin/env python3
"""
Invoice-to-Odoo Telegram Bot
Send a photo + command to the bot → it extracts data → posts to Odoo 13.

Usage:
  /start           — Welcome message
  /invoice         — Next photo = invoice (AP + inventory)
  /expense         — Next photo = expense entry
  /receipt         — Next photo = receipt
  /status          — Check Ollama & Odoo connection
  /help            — Show commands

Or just send a photo with caption: "invoice", "expense", "receipt"
"""

import os
import sys
import json
import logging
import tempfile
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from extract import extract_invoice_data
from post_odoo import OdooPoster

# ─── Config ───────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")

# ─── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log"),
    ],
)
log = logging.getLogger("invoice-bot")

# ─── State ────────────────────────────────────────────────────────
# Track what mode each user is in (invoice / expense / receipt)
user_modes: dict[int, str] = {}
poster = None  # Lazy init


def get_poster():
    global poster
    if poster is None:
        poster = OdooPoster()
    return poster


# ─── Commands ─────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Welcome message with keyboard."""
    keyboard = [
        [KeyboardButton("📸 Invoice"), KeyboardButton("💸 Expense")],
        [KeyboardButton("🧾 Receipt"), KeyboardButton("📊 Status")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👋 *Invoice-to-Odoo Bot*\n\n"
        "Send me a photo of an invoice, receipt, or expense\n"
        "and I'll extract the data and post it to your Odoo 13.\n\n"
        "*How to use:*\n"
        "1️⃣ Tap a button below (or type `invoice`/`expense`/`receipt`)\n"
        "2️⃣ Send the photo\n"
        "3️⃣ I'll do the rest ✅\n\n"
        "Or just send a photo with a caption!",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Commands:*\n"
        "`invoice` — Record as vendor bill (AP + inventory)\n"
        "`expense` — Record as expense\n"
        "`receipt` — Record as receipt\n"
        "`status`  — Check Ollama & Odoo connections\n"
        "`help`    — This message\n\n"
        "Or just send a photo with a caption like:\n"
        "📸 _photo_ + \"invoice\"",
        parse_mode="Markdown",
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Check Ollama and Odoo connectivity."""
    lines = []

    # Check Ollama
    import requests
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    try:
        r = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if r.ok:
            models = r.json().get("models", [])
            model_names = [m["name"] for m in models[:5]]
            lines.append(f"✅ Ollama: Connected ({len(models)} models)")
            if model_names:
                lines.append(f"   Models: {', '.join(model_names)}")
        else:
            lines.append(f"⚠️ Ollama: Responded with {r.status_code}")
    except Exception as e:
        lines.append(f"❌ Ollama: {e}")

    # Check Odoo
    try:
        p = get_poster()
        p._connect()
        lines.append(f"✅ Odoo: Connected (uid={p._uid})")
    except Exception as e:
        lines.append(f"❌ Odoo: {e}")

    await update.message.reply_text("\n".join(lines))


# ─── Text Handler (mode selection) ────────────────────────────────

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle text messages — set mode."""
    text = (update.message.text or "").lower().strip()

    mode_map = {
        "📸 invoice": "invoice",
        "invoice": "invoice",
        "💸 expense": "expense",
        "expense": "expense",
        "🧾 receipt": "receipt",
        "receipt": "receipt",
        "📊 status": "status",
    }

    if text in ("📊 status", "status"):
        await cmd_status(update, ctx)
        return

    if text in ("help", "/help"):
        await cmd_help(update, ctx)
        return

    mode = mode_map.get(text)
    if mode:
        user_modes[update.effective_chat.id] = mode
        emoji = {"invoice": "📄", "expense": "💸", "receipt": "🧾"}
        await update.message.reply_text(
            f"{emoji.get(mode, '📸')} Mode set to *{mode}*\n"
            f"Now send me the photo!",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "🤔 Send a photo, or tap one of the buttons below.\n"
            "Type `help` for commands.",
            parse_mode="Markdown",
        )


# ─── Photo Handler (main processing) ─────────────────────────────

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Process incoming photo: extract → post to Odoo."""
    chat_id = update.effective_chat.id

    # Determine mode from caption or stored mode
    caption = (update.message.caption or "").lower().strip()
    mode = None
    if "invoice" in caption:
        mode = "invoice"
    elif "expense" in caption:
        mode = "expense"
    elif "receipt" in caption:
        mode = "receipt"
    else:
        mode = user_modes.get(chat_id, "invoice")  # default to invoice

    # Send "processing" message
    processing_msg = await update.message.reply_text(
        f"⏳ Processing as *{mode}*...\n"
        f"📸 Downloading image...",
        parse_mode="Markdown",
    )

    try:
        # ── Download photo ──
        photo = update.message.photo[-1]  # Highest resolution
        file = await ctx.bot.get_file(photo.file_id)

        # Save to temp file
        suffix = ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
        await file.download_to_drive(tmp_path)

        await processing_msg.edit_text(
            f"⏳ Processing as *{mode}*...\n"
            f"🔍 Extracting data with AI...",
            parse_mode="Markdown",
        )

        # ── Extract with Ollama ──
        data = extract_invoice_data(tmp_path)
        if not data:
            await processing_msg.edit_text(
                "❌ *Extraction failed!*\n\n"
                "Couldn't read data from the image.\n"
                "Make sure the image is clear and Ollama is running.",
                parse_mode="Markdown",
            )
            os.unlink(tmp_path)
            return

        # Save extracted data
        json_path = tmp_path.replace(suffix, ".json")
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Build summary
        summary = format_summary(data, mode)

        await processing_msg.edit_text(
            f"⏳ Processing as *{mode}*...\n"
            f"✅ Data extracted\n"
            f"📤 Posting to Odoo...",
            parse_mode="Markdown",
        )

        # ── Post to Odoo ──
        p = get_poster()
        supplier_name = data.get("supplier_name") or "Unknown Supplier"
        partner_id = p.find_or_create_supplier(
            supplier_name, data.get("supplier_vat")
        )

        results = {"partner_id": partner_id}

        if mode == "invoice":
            results["vendor_bill_id"] = p.create_vendor_bill(data, partner_id)
            try:
                inv = p.create_inventory_receipt(data, partner_id)
                if inv:
                    results["inventory_receipt_id"] = inv
            except Exception as e:
                results["inventory_error"] = str(e)

        elif mode == "expense":
            results["expense_id"] = p.create_expense(data, partner_id)

        elif mode == "receipt":
            results["vendor_bill_id"] = p.create_vendor_bill(data, partner_id)
            results["expense_id"] = p.create_expense(data, partner_id)

        # ── Done ──
        odoo_links = []
        if results.get("vendor_bill_id"):
            odoo_links.append(f"📄 Bill #{results['vendor_bill_id']}")
        if results.get("inventory_receipt_id"):
            odoo_links.append(f"📦 Inventory #{results['inventory_receipt_id']}")
        if results.get("expense_id"):
            odoo_links.append(f"💰 Expense #{results['expense_id']}")

        await processing_msg.edit_text(
            f"✅ *Done!*\n\n"
            f"*Mode:* {mode}\n"
            f"*Supplier:* {supplier_name}\n"
            f"*Total:* {data.get('currency', '')} {data.get('total_amount', '?')}\n\n"
            f"*Created in Odoo:*\n" + "\n".join(odoo_links) + "\n\n"
            f"---\n{summary}",
            parse_mode="Markdown",
        )

        # Cleanup
        os.unlink(tmp_path)
        if os.path.exists(json_path):
            os.unlink(json_path)

        # Reset mode
        user_modes.pop(chat_id, None)

    except Exception as e:
        log.error(f"❌ Failed to process photo: {e}")
        await processing_msg.edit_text(
            f"❌ *Error!*\n\n`{e}`\n\n"
            f"Check your .env config and try again.",
            parse_mode="Markdown",
        )


def format_summary(data: dict, mode: str) -> str:
    """Format extracted data as readable summary."""
    lines = []
    lines.append(f"*Extracted Data:*")
    if data.get("invoice_number"):
        lines.append(f"  Invoice #: {data['invoice_number']}")
    if data.get("invoice_date"):
        lines.append(f"  Date: {data['invoice_date']}")
    if data.get("subtotal"):
        lines.append(f"  Subtotal: {data['subtotal']}")
    if data.get("tax_amount"):
        lines.append(f"  Tax: {data['tax_amount']}")
    if data.get("total_amount"):
        lines.append(f"  Total: {data['total_amount']}")
    if data.get("line_items"):
        lines.append(f"  Items: {len(data['line_items'])}")
        for item in data["line_items"][:3]:
            lines.append(f"    • {item.get('description', '?')} × {item.get('quantity', 1)}")
        if len(data["line_items"]) > 3:
            lines.append(f"    ... +{len(data['line_items']) - 3} more")
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN not set in .env")
        print("   1. Talk to @BotFather on Telegram")
        print("   2. /newbot → get your token")
        print("   3. Add it to .env: TELEGRAM_TOKEN=your_token_here")
        sys.exit(1)

    log.info("🤖 Starting Invoice-to-Odoo Bot...")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("invoice", lambda u, c: set_mode(u, c, "invoice")))
    app.add_handler(CommandHandler("expense", lambda u, c: set_mode(u, c, "expense")))
    app.add_handler(CommandHandler("receipt", lambda u, c: set_mode(u, c, "receipt")))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    log.info("🤖 Bot is running. Press Ctrl+C to stop.")
    app.run_polling()


async def set_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE, mode: str):
    user_modes[update.effective_chat.id] = mode
    emoji = {"invoice": "📄", "expense": "💸", "receipt": "🧾"}
    await update.message.reply_text(
        f"{emoji.get(mode, '📸')} Mode set to *{mode}*. Send the photo!",
        parse_mode="Markdown",
    )


if __name__ == "__main__":
    main()
