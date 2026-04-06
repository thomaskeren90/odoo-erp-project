"""
Odoo 13 Receipt Scanner — AI Vision Edition
=============================================
Take a photo of an invoice/receipt → AI reads it → saves to Odoo 13.

Uses multimodal AI (Ollama/OpenAI/Gemini) instead of Tesseract OCR.
Much better at reading Indonesian receipts, handwriting, messy formats.

Usage:
  1. python3 app.py
  2. Open http://localhost:5000 on your phone
  3. Take a photo of a receipt
  4. AI extracts the data
  5. Review and save to Odoo
"""

import os
import re
import json
import base64
import xmlrpc.client
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

from config import (
    ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD,
    OLLAMA_URL, OLLAMA_MODEL,
    OPENAI_API_KEY, OPENAI_MODEL,
    GEMINI_API_KEY,
    AI_PROVIDER,
    UPLOAD_FOLDER, HOST, PORT
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# ODOO CONNECTION
# ═══════════════════════════════════════════════════════════════

def odoo_connect():
    """Connect to Odoo 13 via XML-RPC."""
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
    if not uid:
        raise Exception("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return common, models, uid


def odoo_search_read(models, uid, model, domain=None, fields=None, limit=20):
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, 'search_read', domain or [],
        {'fields': fields or ['name'], 'limit': limit}
    )


def odoo_create(models, uid, model, vals):
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, 'create', [vals]
    )


# ═══════════════════════════════════════════════════════════════
# AI VISION — replaces Tesseract OCR
# ═══════════════════════════════════════════════════════════════

EXTRACTION_PROMPT = """You are a receipt/invoice data extractor. Analyze this image and extract ALL information.

Return ONLY valid JSON (no markdown, no explanation):

{
  "supplier": "company or shop name",
  "date": "YYYY-MM-DD",
  "total": "total amount as number (no dots/commas)",
  "subtotal": "subtotal as number if visible",
  "tax": "tax amount if visible",
  "items": [
    {"name": "item description", "qty": 1, "price": 10000, "total": 10000}
  ],
  "currency": "IDR",
  "receipt_number": "invoice/receipt number if visible",
  "payment_method": "cash/card/transfer if visible",
  "notes": "any other relevant info",
  "confidence": "high/medium/low"
}

Rules:
- Indonesian receipts often use dots as thousand separators (Rp 150.000 = 150000)
- Remove "Rp", ".", spaces from amounts — just the number
- If you can't read something clearly, use null
- For date, look for patterns like 01/02/2025, 1 Jan 2025, etc."""


def encode_image_base64(image_path):
    """Read image and encode to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_with_ollama(image_path):
    """Use local Ollama with vision model."""
    b64 = encode_image_base64(image_path)
    ext = os.path.splitext(image_path)[1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")

    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": EXTRACTION_PROMPT,
            "images": [b64],
            "stream": False,
            "options": {"temperature": 0.1}
        },
        timeout=120
    )
    resp.raise_for_status()
    text = resp.json()["response"]
    return _parse_ai_response(text)


def extract_with_openai(image_path):
    """Use OpenAI GPT-4o-mini vision."""
    b64 = encode_image_base64(image_path)
    ext = os.path.splitext(image_path)[1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": OPENAI_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                ]
            }],
            "max_tokens": 1000,
            "temperature": 0.1
        },
        timeout=60
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    return _parse_ai_response(text)


def extract_with_gemini(image_path):
    """Use Google Gemini Flash vision."""
    b64 = encode_image_base64(image_path)
    ext = os.path.splitext(image_path)[1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")

    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
        json={
            "contents": [{
                "parts": [
                    {"text": EXTRACTION_PROMPT},
                    {"inline_data": {"mime_type": mime, "data": b64}}
                ]
            }],
            "generationConfig": {"temperature": 0.1}
        },
        timeout=60
    )
    resp.raise_for_status()
    parts = resp.json()["candidates"][0]["content"]["parts"]
    text = parts[0]["text"]
    return _parse_ai_response(text)


def _parse_ai_response(text):
    """Extract JSON from AI response (handles markdown wrapping)."""
    # Strip markdown code blocks if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    # Find JSON object
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        data = json.loads(match.group())
        # Normalize total to integer
        if data.get("total"):
            data["total"] = clean_amount(str(data["total"]))
        if data.get("subtotal"):
            data["subtotal"] = clean_amount(str(data["subtotal"]))
        if data.get("tax"):
            data["tax"] = clean_amount(str(data["tax"]))
        return data
    return {"error": "Could not parse AI response", "raw": text}


def clean_amount(amount_str):
    """Convert '150.000' or 'Rp 1.500.000' to integer 150000 or 1500000."""
    if not amount_str:
        return 0
    # Remove non-numeric except dots and commas
    cleaned = re.sub(r'[^\d.,]', '', str(amount_str))
    if not cleaned:
        return 0
    # Indonesian: dots = thousands, comma = decimal
    # If format is like 1.500.000, remove all dots
    if '.' in cleaned and len(cleaned.split('.')[-1]) == 3:
        cleaned = cleaned.replace('.', '')
    # If comma is decimal separator
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
    try:
        return int(float(cleaned))
    except ValueError:
        return 0


def extract_receipt_data(image_path):
    """Try AI providers in order until one works."""
    providers = []

    # Build provider list based on config
    if AI_PROVIDER == "ollama" and OLLAMA_URL:
        providers.append(("Ollama", extract_with_ollama))
    if AI_PROVIDER == "openai" and OPENAI_API_KEY:
        providers.append(("OpenAI", extract_with_openai))
    if AI_PROVIDER == "gemini" and GEMINI_API_KEY:
        providers.append(("Gemini", extract_with_gemini))

    # Add fallbacks
    if OPENAI_API_KEY and AI_PROVIDER != "openai":
        providers.append(("OpenAI", extract_with_openai))
    if GEMINI_API_KEY and AI_PROVIDER != "gemini":
        providers.append(("Gemini", extract_with_gemini))
    if OLLAMA_URL and AI_PROVIDER != "ollama":
        providers.append(("Ollama", extract_with_ollama))

    last_error = None
    for name, fn in providers:
        try:
            print(f"  Trying {name}...")
            result = fn(image_path)
            result["ai_provider"] = name
            if not result.get("error"):
                return result
            last_error = result.get("error")
        except Exception as e:
            last_error = str(e)
            print(f"  {name} failed: {e}")
            continue

    return {"error": f"All AI providers failed. Last error: {last_error}"}


# ═══════════════════════════════════════════════════════════════
# FLASK ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/scan', methods=['POST'])
def scan_receipt():
    """Upload receipt image, extract data with AI."""
    if 'photo' not in request.files:
        return jsonify({"error": "No photo uploaded"}), 400

    file = request.files['photo']
    if not file.filename:
        return jsonify({"error": "Empty file"}), 400

    # Save uploaded file
    ext = os.path.splitext(file.filename)[1] or '.jpg'
    filename = f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    print(f"\n📸 Processing: {filename}")

    # Extract with AI
    ocr_data = extract_receipt_data(filepath)
    print(f"  Result: supplier={ocr_data.get('supplier')}, total={ocr_data.get('total')}")

    # Get Odoo accounts and products for selection
    try:
        common, models, uid = odoo_connect()
        accounts = odoo_search_read(models, uid, 'account.account',
            domain=[('internal_type', 'in', ['payable', 'receivable', 'other'])],
            fields=['code', 'name'], limit=100)
        products = odoo_search_read(models, uid, 'product.product',
            fields=['default_code', 'name'], limit=100)
    except Exception as e:
        accounts = []
        products = []
        ocr_data['odoo_error'] = str(e)

    return jsonify({
        "ocr": ocr_data,
        "accounts": accounts,
        "products": products,
        "filename": filename
    })


@app.route('/submit', methods=['POST'])
def submit_to_odoo():
    """Save extracted data to Odoo 13."""
    data = request.json
    try:
        common, models, uid = odoo_connect()

        if data['type'] == 'expense':
            # Create vendor bill (account.move)
            vals = {
                'move_type': 'in_invoice',
                'partner_id': _get_or_create_partner(models, uid, data.get('supplier', 'Unknown')),
                'invoice_date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'ref': data.get('description', 'Receipt scan'),
                'invoice_line_ids': [(0, 0, {
                    'name': data.get('description', 'Expense from receipt'),
                    'quantity': 1,
                    'price_unit': _parse_amount(data.get('amount', 0)),
                    'account_id': int(data['account_id']) if data.get('account_id') else _get_default_expense_account(models, uid),
                })]
            }
            move_id = odoo_create(models, uid, 'account.move', vals)
            return jsonify({"success": True, "message": f"Expense created (ID: {move_id})", "id": move_id})

        elif data['type'] == 'cogs':
            # Create vendor bill for inventory purchase
            product_id = int(data['product_id']) if data.get('product_id') else None
            if not product_id:
                return jsonify({"success": False, "error": "Please select a product for COGS entry"})

            vals = {
                'move_type': 'in_invoice',
                'partner_id': _get_or_create_partner(models, uid, data.get('supplier', 'Unknown')),
                'invoice_date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'ref': data.get('description', 'Inventory purchase from receipt'),
                'invoice_line_ids': [(0, 0, {
                    'product_id': product_id,
                    'name': data.get('description', 'Inventory purchase'),
                    'quantity': 1,
                    'price_unit': _parse_amount(data.get('amount', 0)),
                })]
            }
            move_id = odoo_create(models, uid, 'account.move', vals)
            return jsonify({"success": True, "message": f"Purchase created (ID: {move_id})", "id": move_id})

        else:
            return jsonify({"success": False, "error": "Invalid type"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def _get_or_create_partner(models, uid, name):
    """Find or create a supplier partner in Odoo."""
    partners = odoo_search_read(models, uid, 'res.partner',
        domain=[('name', '=', name)], fields=['id'], limit=1)
    if partners:
        return partners[0]['id']
    return odoo_create(models, uid, 'res.partner', {
        'name': name,
        'supplier_rank': 1,
        'company_type': 'company'
    })


def _get_default_expense_account(models, uid):
    """Get default expense account."""
    accounts = odoo_search_read(models, uid, 'account.account',
        domain=[('code', '=', '611003')], fields=['id'], limit=1)
    if accounts:
        return accounts[0]['id']
    return None


def _parse_amount(val):
    """Convert amount to float."""
    if isinstance(val, (int, float)):
        return float(val)
    return clean_amount(str(val))


# ═══════════════════════════════════════════════════════════════
# HTML TEMPLATE (phone-friendly)
# ═══════════════════════════════════════════════════════════════

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Receipt Scanner</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, monospace; background: #f5f5f5; padding: 12px; }
h1 { font-size: 20px; margin-bottom: 12px; text-align: center; }

/* Upload */
.upload-area { background: white; border: 2px dashed #ccc; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 12px; }
.upload-label { display: block; font-size: 15px; color: #666; cursor: pointer; }
.upload-label .icon { font-size: 40px; display: block; margin-bottom: 6px; }
input[type="file"] { display: none; }
.btn { border: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; cursor: pointer; margin: 4px; color: white; }
.btn-cam { background: #4CAF50; }
.btn-gal { background: #2196F3; }

/* Loading */
#loading { display: none; text-align: center; padding: 20px; }
.spinner { border: 4px solid #f3f3f3; border-top: 4px solid #4CAF50; border-radius: 50%; width: 36px; height: 36px; animation: spin 1s linear infinite; margin: 0 auto 8px; }
@keyframes spin { 100% { transform: rotate(360deg); } }

/* Results */
#results { display: none; }
.side-by-side { display: flex; gap: 12px; }
.image-col { flex: 1; min-width: 0; }
.image-col img { width: 100%; border-radius: 8px; border: 1px solid #ddd; }
.text-col { flex: 1; min-width: 0; }
.extracted-box { background: white; border: 1px solid #ddd; border-radius: 8px; padding: 12px; font-family: monospace; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-break: break-all; max-height: 70vh; overflow-y: auto; }
.extracted-box .tag { color: #1565c0; font-weight: bold; }
.extracted-box .val { color: #222; }
.extracted-box .line { border-bottom: 1px solid #eee; padding: 2px 0; }

/* Mobile: stack */
@media (max-width: 700px) {
  .side-by-side { flex-direction: column; }
  .image-col img { max-height: 350px; object-fit: contain; }
}

/* Action bar */
.action-bar { margin-top: 12px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.btn-edit { background: #FF9800; }
.btn-save { background: #4CAF50; }
.btn-save:disabled { background: #ccc; }
.progress-text { font-size: 12px; color: #666; }
#status { padding: 10px; border-radius: 8px; margin-top: 10px; display: none; font-size: 14px; }
.success { background: #e8f5e9; color: #2e7d32; }
.error { background: #ffebee; color: #c62828; }

/* Edit modal */
#editModal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 100; justify-content: center; align-items: center; }
#editModal.show { display: flex; }
.modal-content { background: white; border-radius: 12px; padding: 20px; width: 90%; max-width: 500px; max-height: 80vh; overflow-y: auto; }
.modal-content h3 { margin-bottom: 12px; }
.modal-content .field { margin-bottom: 10px; }
.modal-content .field label { display: block; font-size: 12px; color: #666; margin-bottom: 2px; }
.modal-content .field input, .modal-content .field select, .modal-content .field textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.modal-actions { display: flex; gap: 8px; margin-top: 14px; }
.btn-cancel { background: #9e9e9e; }
.btn-confirm { background: #4CAF50; }
.ai-badge { display: inline-block; background: #e3f2fd; color: #1565c0; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-left: 8px; }
</style>
</head>
<body>
<h1>📸 Receipt Scanner</h1>

<div class="upload-area">
    <label class="upload-label" for="photo">
        <span class="icon">📱</span>
        Take photo or upload receipt
    </label>
    <input type="file" id="photo" accept="image/*" capture="environment">
    <div style="margin-top:10px">
        <button class="btn btn-cam" onclick="document.getElementById('photo').capture='environment'; document.getElementById('photo').click()">📷 Camera</button>
        <button class="btn btn-gal" onclick="document.getElementById('photo').capture=''; document.getElementById('photo').click()">🖼️ Gallery</button>
    </div>
</div>

<img id="previewImg" style="display:none">
<div id="loading">
    <div class="spinner"></div>
    <p>AI is reading your receipt...</p>
</div>

<div id="results">
    <div style="margin-bottom:8px; font-weight:600;">Extracted Data <span id="aiBadge" class="ai-badge"></span></div>
    <div class="side-by-side">
        <div class="image-col">
            <div style="font-size:12px; color:#666; margin-bottom:4px;">📷 Original</div>
            <img id="resultImg">
        </div>
        <div class="text-col">
            <div style="font-size:12px; color:#666; margin-bottom:4px;">📄 Extracted</div>
            <div class="extracted-box" id="extractedText"></div>
        </div>
    </div>

    <div class="action-bar">
        <span class="progress-text" id="checkProgress"></span>
        <div style="flex:1"></div>
        <button class="btn btn-edit" onclick="openEdit()">✏️ Edit</button>
        <button class="btn btn-save" id="saveBtn" onclick="saveToOdoo()" disabled>✅ Save to Odoo</button>
    </div>
    <div id="status"></div>
</div>

<!-- Edit modal -->
<div id="editModal">
    <div class="modal-content">
        <h3>✏️ Edit Extracted Data</h3>
        <div class="field"><label>Supplier</label><input id="ed_supplier"></div>
        <div class="field"><label>Date (YYYY-MM-DD)</label><input id="ed_date"></div>
        <div class="field"><label>Amount (Rp)</label><input id="ed_amount" type="number" inputmode="numeric"></div>
        <div class="field"><label>Description / Notes</label><textarea id="ed_description" rows="2"></textarea></div>
        <div class="field">
            <label>Type</label>
            <select id="ed_type">
                <option value="">-- Select --</option>
                <option value="expense">💰 Expense</option>
                <option value="cogs">📦 Inventory/COGS</option>
            </select>
        </div>
        <div id="ed_expense_wrap" style="display:none">
            <div class="field"><label>Account</label><select id="ed_account"><option value="">-- Select --</option></select></div>
        </div>
        <div id="ed_cogs_wrap" style="display:none">
            <div class="field"><label>Product</label><select id="ed_product"><option value="">-- Select --</option></select></div>
        </div>
        <div class="modal-actions">
            <button class="btn btn-cancel" onclick="closeEdit()">Cancel</button>
            <button class="btn btn-confirm" onclick="confirmEdit()">✓ Confirm</button>
        </div>
    </div>
</div>

<script>
let ocrData = {}, currentFilename = '', selectedType = '', confirmed = false;

document.getElementById('photo').addEventListener('change', function() {
    if (!this.files[0]) return;
    confirmed = false;
    const fd = new FormData();
    fd.append('photo', this.files[0]);

    // Store image for preview
    const reader = new FileReader();
    reader.onload = e => { document.getElementById('previewImg').src = e.target.result; };
    reader.readAsDataURL(this.files[0]);

    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';

    fetch('/scan', {method:'POST', body:fd})
    .then(r => r.json())
    .then(data => {
        document.getElementById('loading').style.display = 'none';
        if (data.error) { alert('Error: '+data.error); return; }
        showResults(data);
    })
    .catch(err => {
        document.getElementById('loading').style.display = 'none';
        alert('Failed: '+err.message);
    });
});

// Type selector in modal
document.getElementById('ed_type').addEventListener('change', function() {
    selectedType = this.value;
    document.getElementById('ed_expense_wrap').style.display = selectedType==='expense'?'block':'none';
    document.getElementById('ed_cogs_wrap').style.display = selectedType==='cogs'?'block':'none';
    updateSaveBtn();
});

function showResults(data) {
    ocrData = data.ocr;
    currentFilename = data.filename;

    // Show original image
    document.getElementById('resultImg').src = document.getElementById('previewImg')?.src || '';

    // Show extracted data as readable text
    document.getElementById('extractedText').innerHTML = formatExtracted(ocrData);
    document.getElementById('aiBadge').textContent = ocrData.ai_provider || 'AI';

    // Populate edit fields
    document.getElementById('ed_supplier').value = ocrData.supplier || '';
    document.getElementById('ed_date').value = ocrData.date || '';
    document.getElementById('ed_amount').value = ocrData.total || '';
    document.getElementById('ed_description').value = ocrData.notes || '';
    selectedType = '';
    document.getElementById('ed_type').value = '';
    document.getElementById('ed_expense_wrap').style.display = 'none';
    document.getElementById('ed_cogs_wrap').style.display = 'none';

    // Populate dropdowns
    const aSel = document.getElementById('ed_account');
    aSel.innerHTML = '<option value="">-- Select account --</option>';
    (data.accounts||[]).forEach(a => aSel.innerHTML += '<option value="'+a.id+'">'+a.code+' - '+a.name+'</option>');

    const pSel = document.getElementById('ed_product');
    pSel.innerHTML = '<option value="">-- Select product --</option>';
    (data.products||[]).forEach(p => pSel.innerHTML += '<option value="'+p.id+'">'+(p.default_code?p.default_code+' - ':'')+p.name+'</option>');

    // Show, require edit
    confirmed = false;
    updateSaveBtn();
    document.getElementById('results').style.display = 'block';
}

function formatExtracted(d) {
    let lines = [];
    const add = (tag, val) => {
        if (val !== null && val !== undefined && val !== '') {
            lines.push('<div class="line"><span class="tag">'+tag+':</span> <span class="val">'+val+'</span></div>');
        }
    };
    add('SUPPLIER', d.supplier);
    add('DATE', d.date);
    add('TOTAL', d.total ? 'Rp '+Number(d.total).toLocaleString('id-ID') : null);
    add('SUBTOTAL', d.subtotal ? 'Rp '+Number(d.subtotal).toLocaleString('id-ID') : null);
    add('TAX', d.tax ? 'Rp '+Number(d.tax).toLocaleString('id-ID') : null);
    add('RECEIPT #', d.receipt_number);
    add('PAYMENT', d.payment_method);
    add('CURRENCY', d.currency);
    add('CONFIDENCE', d.confidence);

    if (d.items && d.items.length > 0) {
        lines.push('<div class="line" style="margin-top:6px;"><span class="tag">ITEMS:</span></div>');
        d.items.forEach((item, i) => {
            let itemLine = '  ' + (i+1) + '. ' + (item.name||'?');
            if (item.qty) itemLine += ' x' + item.qty;
            if (item.price) itemLine += ' @ Rp ' + Number(item.price).toLocaleString('id-ID');
            if (item.total) itemLine += ' = Rp ' + Number(item.total).toLocaleString('id-ID');
            lines.push('<div class="line" style="color:#555">'+itemLine+'</div>');
        });
    }

    if (d.notes) {
        lines.push('<div class="line" style="margin-top:6px;"><span class="tag">NOTES:</span> <span class="val">'+d.notes+'</span></div>');
    }

    // Raw text in collapsible
    if (d.raw_text) {
        lines.push('<details style="margin-top:8px"><summary style="font-size:11px;color:#999;cursor:pointer">Raw text</summary><div style="font-size:11px;color:#888;white-space:pre-wrap;max-height:120px;overflow-y:auto">'+d.raw_text+'</div></details>');
    }

    return lines.join('\n');
}

function openEdit() {
    document.getElementById('editModal').classList.add('show');
}

function closeEdit() {
    document.getElementById('editModal').classList.remove('show');
}

function confirmEdit() {
    confirmed = true;
    closeEdit();

    // Update the displayed text with edited values
    const edited = {...ocrData};
    edited.supplier = document.getElementById('ed_supplier').value;
    edited.date = document.getElementById('ed_date').value;
    edited.total = document.getElementById('ed_amount').value;
    edited.notes = document.getElementById('ed_description').value;
    document.getElementById('extractedText').innerHTML = formatExtracted(edited);

    updateSaveBtn();
}

function updateSaveBtn() {
    const btn = document.getElementById('saveBtn');
    const prog = document.getElementById('checkProgress');
    if (confirmed && selectedType) {
        btn.disabled = false;
        btn.textContent = '✅ Save to Odoo';
        prog.textContent = '✓ Verified & categorized';
    } else {
        btn.disabled = true;
        const steps = [];
        if (!confirmed) steps.push('review data');
        if (!selectedType) steps.push('select type');
        btn.textContent = '✅ Save to Odoo';
        prog.textContent = '⚠️ Please: ' + steps.join(', ');
    }
}

function saveToOdoo() {
    const btn = document.getElementById('saveBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Saving...';

    fetch('/submit', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
            type: selectedType,
            supplier: document.getElementById('ed_supplier').value,
            amount: document.getElementById('ed_amount').value,
            description: document.getElementById('ed_description').value,
            account_id: document.getElementById('ed_account').value || null,
            product_id: document.getElementById('ed_product').value || null,
            filename: currentFilename
        })
    })
    .then(r => r.json())
    .then(data => {
        const s = document.getElementById('status');
        s.style.display = 'block';
        if (data.success) {
            s.className = 'success';
            s.textContent = '✅ ' + data.message;
            btn.textContent = '✅ Saved!';
        } else {
            s.className = 'error';
            s.textContent = '❌ ' + data.error;
            btn.disabled = false;
            btn.textContent = '✅ Save to Odoo';
        }
    })
    .catch(err => {
        btn.disabled = false;
        btn.textContent = '✅ Save to Odoo';
        alert('Save failed: ' + err.message);
    });
}
</script>
</body>
</html>
"""

if __name__ == '__main__':
    print("🚀 Receipt Scanner (AI Vision)")
    print(f"📡 Odoo: {ODOO_URL} / DB: {ODOO_DB}")
    print(f"🤖 AI: {AI_PROVIDER}")
    print(f"🌐 Open: http://localhost:{PORT}")
    print(f"📱 Phone: http://<your-laptop-ip>:{PORT}")
    app.run(host=HOST, port=PORT, debug=True)
