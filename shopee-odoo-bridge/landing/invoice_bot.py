import json, re, logging, xmlrpc.client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google import genai
import PIL.Image

logging.basicConfig(level=logging.INFO)
TELEGRAM_TOKEN = "8701861548:AAEDsw1EX9KRrxw2gfVxue-dp04A5AYnxBs"
GEMINI_API_KEY = "AIzaSyAbNFQqmn0UxHOgT7Tg-3lEhTXSr9rfB_Y"
MY_CHAT_ID = 1306395687
ODOO_URL = "http://localhost:8069"
ODOO_DB = "tokoodoo13"
ODOO_USER = "tokomakmur"
ODOO_PASSWORD = "admin123"
gemini = genai.Client(api_key=GEMINI_API_KEY)
pending = {}

def extract_invoice(image_path):
    image = PIL.Image.open(image_path)
    prompt = "You are an invoice OCR assistant. Look at this invoice image. Return ONLY valid JSON with fields: supplier, invoice_number, date, type (invoice or expense), lines (array of description/qty/unit_price/total), subtotal, tax, total, currency. Use null for missing fields. No markdown, no explanation."
    response = gemini.models.generate_content(model="gemini-2.5-flash", contents=[prompt, image])
    text = re.sub(r"```json|```", "", response.text.strip()).strip()
    return json.loads(text)

def format_preview(data):
    lines = "\n".join([f"  - {l['description']} x{l['qty']} @ {l['unit_price']:,} = {l['total']:,}" for l in data.get("lines", [])])
    return f"Invoice Preview\n\nSupplier: {data.get('supplier')}\nInvoice No: {data.get('invoice_number')}\nDate: {data.get('date')}\nType: {data.get('type')}\n\nItems:\n{lines}\n\nTax: {data.get('tax') or 0:,}\nTotal: IDR {data.get('total'):,}\n\nApprove to post to Odoo?"

def odoo_connect():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models

def get_or_create_supplier(uid, models, name):
    ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "res.partner", "search", [[["name", "ilike", name], ["supplier_rank", ">", 0]]])
    if ids:
        return ids[0]
    return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "res.partner", "create", [{"name": name, "supplier_rank": 1, "customer_rank": 0}])

def post_to_odoo(data):
    uid, models = odoo_connect()
    supplier_id = get_or_create_supplier(uid, models, data["supplier"])
    lines = [(0, 0, {"name": l["description"], "quantity": l["qty"], "price_unit": l["unit_price"]}) for l in data.get("lines", [])]
    invoice_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "account.move", "create", [{"type": "in_invoice", "partner_id": supplier_id, "invoice_date": data.get("date"), "ref": data.get("invoice_number"), "invoice_line_ids": lines}])
    models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "account.move", "action_post", [[invoice_id]])
    return invoice_id

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != MY_CHAT_ID:
        return
    await update.message.reply_text("Photo received. Extracting invoice data...")
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    path = f"/tmp/invoice_{photo.file_id}.jpg"
    await file.download_to_drive(path)
    try:
        data = extract_invoice(path)
        pending[str(update.message.message_id)] = data
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Approve", callback_data=f"approve_{update.message.message_id}"), InlineKeyboardButton("Reject", callback_data=f"reject_{update.message.message_id}")]])
        await update.message.reply_text(format_preview(data), reply_markup=keyboard)
    except Exception as e:
        await update.message.reply_text(f"Failed to extract: {str(e)}")

async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, msg_id = query.data.split("_", 1)
    if action == "reject":
        pending.pop(msg_id, None)
        await query.edit_message_text("Invoice rejected and discarded.")
        return
    data = pending.pop(msg_id, None)
    if not data:
        await query.edit_message_text("Invoice data expired. Please resend photo.")
        return
    await query.edit_message_text("Posting to Odoo...")
    try:
        invoice_id = post_to_odoo(data)
        await query.edit_message_text(f"Posted to Odoo!\n\nSupplier: {data['supplier']}\nInvoice ID: {invoice_id}\nTotal: IDR {data['total']:,}")
    except Exception as e:
        await query.edit_message_text(f"Odoo posting failed: {str(e)}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_approval))
    print("Bot is running... Send an invoice photo to @Tom2328_bot")
    app.run_polling()

if __name__ == "__main__":
    main()