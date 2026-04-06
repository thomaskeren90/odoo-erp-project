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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Receipt Scanner</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, sans-serif; background: #f5f5f5; padding: 16px; max-width: 500px; margin: 0 auto; }
h1 { font-size: 20px; margin-bottom: 16px; text-align: center; }
.upload-area { background: white; border: 2px dashed #ccc; border-radius: 12px; padding: 32px; text-align: center; margin-bottom: 16px; }
.upload-area:hover { border-color: #4CAF50; }
input[type="file"] { display: none; }
.upload-label { display: block; font-size: 16px; color: #666; cursor: pointer; }
.upload-label .icon { font-size: 48px; display: block; margin-bottom: 8px; }
.camera-btn { background: #4CAF50; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; margin: 8px; cursor: pointer; }
.gallery-btn { background: #2196F3; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; margin: 8px; cursor: pointer; }
#loading { display: none; text-align: center; padding: 20px; }
.spinner { border: 4px solid #f3f3f3; border-top: 4px solid #4CAF50; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 10px; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
#results { display: none; background: white; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
@media (min-width: 768px) {
    .side-by-side { display: flex; gap: 16px; }
    .side-by-side .image-col { flex: 1; }
    .side-by-side .form-col { flex: 1; }
}
@media (max-width: 767px) {
    .side-by-side .image-col { margin-bottom: 16px; }
    .side-by-side .image-col img { max-height: 300px; object-fit: contain; }
}
.field { margin-bottom: 12px; }
.field label { display: block; font-size: 13px; color: #666; margin-bottom: 4px; }
.field input, .field select, .field textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 15px; }
.type-select { display: flex; gap: 10px; margin-bottom: 16px; }
.type-btn { flex: 1; padding: 12px; border: 2px solid #ddd; border-radius: 8px; text-align: center; font-size: 14px; cursor: pointer; background: white; }
.type-btn.selected { border-color: #4CAF50; background: #e8f5e9; }
.submit-btn { width: 100%; padding: 14px; background: #4CAF50; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
.submit-btn:disabled { background: #ccc; }
#status { padding: 12px; border-radius: 8px; margin-top: 12px; display: none; }
.success { background: #e8f5e9; color: #2e7d32; }
.error { background: #ffebee; color: #c62828; }
.raw-text { background: #f9f9f9; padding: 8px; border-radius: 4px; font-size: 12px; max-height: 100px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
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
    <div style="margin-top:12px">
        <button class="camera-btn" onclick="document.getElementById('photo').capture='environment'; document.getElementById('photo').click()">📷 Camera</button>
        <button class="gallery-btn" onclick="document.getElementById('photo').capture=''; document.getElementById('photo').click()">🖼️ Gallery</button>
    </div>
</div>

<div id="preview" style="display:none; margin-bottom:16px;">
    <img id="previewImg" style="width:100%; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
</div>
<div id="loading">
    <div class="spinner"></div>
    <p>AI is reading your receipt...</p>
</div>

<div id="results">
    <h3 style="margin-bottom:12px">Extracted Data <span id="aiBadge" class="ai-badge"></span></h3>
    <div class="side-by-side">
        <div class="image-col">
            <img id="resultImg" style="width:100%; border-radius:8px; border:1px solid #eee;">
        </div>
        <div class="form-col">
            <div class="field"><label>Supplier</label><input id="supplier"></div>
    <div class="field"><label>Amount (Rp)</label><input id="amount" type="number" inputmode="numeric"></div>
    <div class="field"><label>Description</label><textarea id="description" rows="2"></textarea></div>

    <div class="type-select">
        <div class="type-btn" id="btn-expense" onclick="selectType('expense')">💰 Expense</div>
        <div class="type-btn" id="btn-cogs" onclick="selectType('cogs')">📦 Inventory/COGS</div>
    </div>

    <div id="expense-fields" style="display:none">
        <div class="field"><label>Account</label><select id="account_id"><option>-- Select --</option></select></div>
    </div>
    <div id="cogs-fields" style="display:none">
        <div class="field"><label>Product</label><select id="product_id"><option>-- Select --</option></select></div>
    </div>
        </div><!-- end form-col -->
    </div><!-- end side-by-side -->

    <button class="submit-btn" id="submitBtn" onclick="submitEntry()">💾 Save to Odoo</button>
    <div id="status"></div>

    <details style="margin-top:12px">
        <summary style="font-size:12px;color:#999">Raw AI output</summary>
        <div class="raw-text" id="rawText"></div>
    </details>
</div>

<script>
let ocrData = {}, currentFilename = '', selectedType = '';

document.getElementById('photo').addEventListener('change', function(e) {
    if (!this.files[0]) return;
    const fd = new FormData();
    fd.append('photo', this.files[0]);

    // Show preview
    const reader = new FileReader();
    reader.onload = e => {
        document.getElementById('previewImg').src = e.target.result;
        document.getElementById('preview').style.display = 'block';
    };
    reader.readAsDataURL(this.files[0]);

    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';

    fetch('/scan', {method:'POST', body:fd})
    .then(r => r.json())
    .then(data => {
        document.getElementById('loading').style.display = 'none';
        if (data.error) { alert('Error: ' + data.error); return; }
        showResults(data);
    })
    .catch(err => {
        document.getElementById('loading').style.display = 'none';
        alert('Upload failed: ' + err.message);
    });
});

function showResults(data) {
    ocrData = data.ocr;
    currentFilename = data.filename;

    document.getElementById('supplier').value = ocrData.supplier || '';
    document.getElementById('amount').value = ocrData.total || '';
    document.getElementById('description').value = ocrData.notes || '';
    document.getElementById('rawText').textContent = JSON.stringify(ocrData, null, 2);
    // Copy preview to result image
    document.getElementById('resultImg').src = document.getElementById('previewImg').src;

    const badge = document.getElementById('aiBadge');
    badge.textContent = ocrData.ai_provider || 'AI';

    // Accounts
    const sel = document.getElementById('account_id');
    sel.innerHTML = '<option value="">-- Select account --</option>';
    (data.accounts||[]).forEach(a => {
        sel.innerHTML += `<option value="${a.id}">${a.code} - ${a.name}</option>`;
    });

    // Products
    const psel = document.getElementById('product_id');
    psel.innerHTML = '<option value="">-- Select product --</option>';
    (data.products||[]).forEach(p => {
        psel.innerHTML += `<option value="${p.id}">${p.default_code ? p.default_code+' - ' : ''}${p.name}</option>`;
    });

    document.getElementById('results').style.display = 'block';
}

function selectType(type) {
    selectedType = type;
    document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('selected'));
    document.getElementById('btn-'+type).classList.add('selected');
    document.getElementById('expense-fields').style.display = type==='expense'?'block':'none';
    document.getElementById('cogs-fields').style.display = type==='cogs'?'block':'none';
}

function submitEntry() {
    if (!selectedType) { alert('Select Expense or COGS'); return; }
    const btn = document.getElementById('submitBtn');
    btn.disabled = true; btn.textContent = '⏳ Saving...';

    fetch('/submit', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
            type: selectedType,
            supplier: document.getElementById('supplier').value,
            amount: document.getElementById('amount').value,
            description: document.getElementById('description').value,
            account_id: document.getElementById('account_id').value || null,
            product_id: document.getElementById('product_id').value || null,
            filename: currentFilename
        })
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false; btn.textContent = '💾 Save to Odoo';
        const s = document.getElementById('status');
        s.style.display = 'block';
        if (data.success) { s.className='success'; s.textContent='✅ '+data.message; }
        else { s.className='error'; s.textContent='❌ '+data.error; }
    })
    .catch(err => {
        btn.disabled = false; btn.textContent = '💾 Save to Odoo';
        alert('Submit failed: '+err.message);
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
