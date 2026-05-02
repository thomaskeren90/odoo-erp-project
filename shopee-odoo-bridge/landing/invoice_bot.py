import json, re, logging, xmlrpc.client
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google import genai
import PIL.Image

logging.basicConfig(level=logging.INFO)
TELEGRAM_TOKEN = "8701861548:AAEDsw1EX9KRrxw2gfVxue-dp04A5AYnxBs"
GEMINI_API_KEY = "AIzaSyAbNFQqmn0UxHOgT7Tg-3lEhTXSr9rfB_Y"
MY_CHAT_ID     = 1306395687
ODOO_URL       = "http://localhost:8069"
ODOO_DB        = "tokoodoo13"
ODOO_USER      = "tokomakmur"
ODOO_PASSWORD  = "admin123"

# Suppliers who require cash payment upfront before delivery
CASH_UPFRONT_SUPPLIERS = ["irnawati", "efendi"]

gemini  = genai.Client(api_key=GEMINI_API_KEY)
pending = {}  # stores extracted data per chat_id waiting for user choice

# ─── GEMINI OCR ────────────────────────────────────────────────

def extract_invoice(image_path):
    image    = PIL.Image.open(image_path)
    prompt   = (
        "You are an invoice OCR assistant. Look at this image. "
        "Return ONLY valid JSON with fields: "
        "supplier, invoice_number, date, type, "
        "lines (array of description/qty/unit_price/total), "
        "subtotal, tax, total, currency. "
        "Use null for missing fields. No markdown, no explanation."
    )
    response = gemini.models.generate_content(model="gemini-2.5-flash", contents=[prompt, image])
    text     = re.sub(r"```json|```", "", response.text.strip()).strip()
    return json.loads(text)

def extract_po(image_path):
    image    = PIL.Image.open(image_path)
    prompt   = (
        "You are a purchase order OCR assistant. Look at this image. "
        "Return ONLY valid JSON with fields: "
        "supplier, date, "
        "lines (array of product_name/product_code/qty/unit_price/uom). "
        "Use null for missing fields. No markdown, no explanation."
    )
    response = gemini.models.generate_content(model="gemini-2.5-flash", contents=[prompt, image])
    text     = re.sub(r"```json|```", "", response.text.strip()).strip()
    return json.loads(text)

# ─── ODOO ──────────────────────────────────────────────────────

def odoo_connect():
    common = xmlrpc.client.ServerProxy(ODOO_URL + "/xmlrpc/2/common")
    uid    = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(ODOO_URL + "/xmlrpc/2/object")
    return uid, models

def get_or_create_supplier(uid, models, name):
    ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "res.partner", "search",
        [[["name", "ilike", name], ["supplier_rank", ">", 0]]])
    if ids:
        return ids[0]
    return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "res.partner", "create",
        [{"name": name, "supplier_rank": 1, "customer_rank": 0}])

def post_vendor_bill(data):
    uid, models = odoo_connect()
    supplier_id = get_or_create_supplier(uid, models, data["supplier"])
    lines       = [(0, 0, {
        "name":        l["description"],
        "quantity":    l["qty"],
        "price_unit":  l["unit_price"]
    }) for l in data.get("lines", [])]
    invoice_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "account.move", "create", [{
        "type":             "in_invoice",
        "partner_id":       supplier_id,
        "invoice_date":     data.get("date"),
        "ref":              data.get("invoice_number"),
        "invoice_line_ids": lines
    }])
    models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "account.move", "action_invoice_open", [[invoice_id]])
    return invoice_id

def post_cogs(data):
    uid, models = odoo_connect()
    supplier_id = get_or_create_supplier(uid, models, data["supplier"])
    lines       = [(0, 0, {
        "name":        l["description"],
        "quantity":    l["qty"],
        "price_unit":  l["unit_price"]
    }) for l in data.get("lines", [])]
    invoice_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "account.move", "create", [{
        "type":             "in_invoice",
        "partner_id":       supplier_id,
        "invoice_date":     data.get("date"),
        "ref":              data.get("invoice_number"),
        "invoice_line_ids": lines,
        "narration":        "COGS - Goods for resale/inventory"
    }])
    models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "account.move", "action_invoice_open", [[invoice_id]])
    return invoice_id

def post_expense(data):
    uid, models = odoo_connect()
    supplier_id = get_or_create_supplier(uid, models, data["supplier"])
    expense_id  = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "hr.expense", "create", [{
        "name":         data.get("supplier") or "Expense",
        "total_amount": data.get("total"),
        "partner_id":   supplier_id
    }])
    return expense_id

def create_po_from_data(data):
    uid, models = odoo_connect()
    supplier_id = get_or_create_supplier(uid, models, data["supplier"])
    order_lines = []
    for line in data.get("lines", []):
        product = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "product.product", "search_read",
            [[["name", "ilike", line.get("product_name", "")]]],
            {"fields": ["id", "uom_po_id"], "limit": 1})
        if product:
            product_id = product[0]["id"]
            uom_id     = product[0]["uom_po_id"][0]
        else:
            product_id = None
            uom_id     = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "uom.uom", "search",
                [[["name", "=", "Units"]]])[0]
        order_lines.append((0, 0, {
            "name":         line.get("product_name", "Unknown"),
            "product_qty":  line.get("qty", 1),
            "price_unit":   line.get("unit_price", 0),
            "product_uom":  uom_id,
            "date_planned": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
            **({"product_id": product_id} if product_id else {})
        }))
    po_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "purchase.order", "create", [{
        "partner_id": supplier_id,
        "date_order":  datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
        "order_line":  order_lines
    }])
    models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "purchase.order", "button_confirm", [[po_id]])
    po_name = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "purchase.order", "read",
        [[po_id]], {"fields": ["name"]})[0]["name"]
    return po_id, po_name

def is_cash_upfront(supplier_name):
    if not supplier_name:
        return False
    return any(s in supplier_name.lower() for s in CASH_UPFRONT_SUPPLIERS)

# ─── FORMAT PREVIEW ────────────────────────────────────────────

def format_preview(data, mode="invoice"):
    result  = "PREVIEW - Please verify before posting\n"
    result += "=" * 35 + "\n"
    result += f"Supplier   : {data.get('supplier')}
"
    if mode == "invoice":
        result += f"Invoice No : {data.get('invoice_number')}
"
    result += f"Date       : {data.get('date')}

"
    result += "Items:
"
    for l in data.get("lines", []):
        if mode == "invoice":
            result += f"  - {l.get('description','?')} x{l.get('qty','?')} = IDR {l.get('total','?')}
"
        else:
            result += f"  - {l.get('product_name','?')} x{l.get('qty','?')} @ IDR {l.get('unit_price','?')}
"
    result += f"
Total: IDR {data.get('total', '-')}
"
    if is_cash_upfront(data.get("supplier")):
        result += "
⚠️ CASH UPFRONT supplier - payment required before delivery!
"
    result += "
Choose action:"
    return result

# ─── TELEGRAM HANDLERS ─────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != MY_CHAT_ID:
        return
    await update.message.reply_text("📸 Photo received. Reading with AI...")
    photo = update.message.photo[-1]
    file  = await context.bot.get_file(photo.file_id)
    path  = f"/tmp/invoice_{photo.file_id}.jpg"
    await file.download_to_drive(path)

    # Check caption for mode
    caption = (update.message.caption or "").lower()
    mode    = "po" if "po" in caption or "order" in caption else "invoice"

    try:
        if mode == "po":
            data = extract_po(path)
        else:
            data = extract_invoice(path)

        pending[update.message.chat_id] = {"data": data, "mode": mode}
        preview = format_preview(data, mode)

        if mode == "po":
            keyboard = [
                [InlineKeyboardButton("✅ Create PO", callback_data="confirm_po"),
                 InlineKeyboardButton("❌ Cancel",    callback_data="cancel")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("📦 COGS",    callback_data="confirm_cogs"),
                 InlineKeyboardButton("💸 Expense", callback_data="confirm_expense")],
                [InlineKeyboardButton("🧾 Vendor Bill", callback_data="confirm_bill"),
                 InlineKeyboardButton("❌ Cancel",       callback_data="cancel")]
            ]
            if is_cash_upfront(data.get("supplier")):
                keyboard.insert(0, [InlineKeyboardButton(
                    "💵 Cash Upfront Payment", callback_data="confirm_cash")])

        await update.message.reply_text(
            preview,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading photo: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    if chat_id not in pending:
        await query.edit_message_text("❌ No pending data. Please send a photo first.")
        return

    record = pending.pop(chat_id)
    data   = record["data"]
    mode   = record["mode"]
    action = query.data

    try:
        if action == "cancel":
            await query.edit_message_text("❌ Cancelled. Nothing was posted.")

        elif action == "confirm_po":
            po_id, po_name = create_po_from_data(data)
            await query.edit_message_text(
                f"✅ Purchase Order Created!

"
                f"PO Number : {po_name}
"
                f"Supplier  : {data.get('supplier')}

"
                f"When goods arrive, send photo of delivery note with caption: receive {po_name}"
            )

        elif action == "confirm_cogs":
            invoice_id = post_cogs(data)
            await query.edit_message_text(
                f"✅ Posted as COGS!

"
                f"Supplier  : {data.get('supplier')}
"
                f"Total     : IDR {data.get('total')}
"
                f"Odoo ID   : {invoice_id}"
            )

        elif action == "confirm_expense":
            expense_id = post_expense(data)
            await query.edit_message_text(
                f"✅ Posted as Expense!

"
                f"Supplier  : {data.get('supplier')}
"
                f"Total     : IDR {data.get('total')}
"
                f"Odoo ID   : {expense_id}"
            )

        elif action == "confirm_bill":
            invoice_id = post_vendor_bill(data)
            await query.edit_message_text(
                f"✅ Vendor Bill Posted!

"
                f"Supplier  : {data.get('supplier')}
"
                f"Invoice No: {data.get('invoice_number')}
"
                f"Total     : IDR {data.get('total')}
"
                f"Odoo ID   : {invoice_id}"
            )

        elif action == "confirm_cash":
            invoice_id = post_vendor_bill(data)
            await query.edit_message_text(
                f"💵 Cash Upfront Payment Recorded!

"
                f"Supplier  : {data.get('supplier')}
"
                f"Total     : IDR {data.get('total')}
"
                f"Odoo ID   : {invoice_id}

"
                f"⚠️ Remember to pay cash BEFORE delivery!"
            )

    except Exception as e:
        await query.edit_message_text(f"❌ Error posting to Odoo: {e}")

# ─── MAIN ──────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("Bot running! Send a photo to get started.")
    print("Add caption PO or order to create a Purchase Order.")
    app.run_polling()

if __name__ == "__main__":
    main()
