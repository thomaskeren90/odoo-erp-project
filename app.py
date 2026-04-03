"""
Odoo 13 Receipt Scanner
- Upload receipt photos via browser (phone-friendly)
- OCR extracts text
- Choose COGS or Expense
- Creates records in Odoo 13
"""

import os
import re
import json
import uuid
import base64
import xmlrpc.client
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from PIL import Image
import pytesseract

from config import ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, OCR_LANGUAGES, UPLOAD_FOLDER

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─── Odoo Connection ────────────────────────────────────────────────
def odoo_connect():
    """Connect to Odoo 13 via XML-RPC and return common, models, uid."""
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
    if not uid:
        raise Exception("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return common, models, uid


def odoo_search_read(models, uid, model, domain=None, fields=None, limit=20):
    """Helper to search_read in Odoo."""
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, 'search_read',
        domain or [],
        {'fields': fields or ['name'], 'limit': limit}
    )


def odoo_create(models, uid, model, vals):
    """Helper to create a record in Odoo."""
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, 'create', [vals]
    )


# ─── OCR Processing ─────────────────────────────────────────────────
def extract_receipt_data(image_path):
    """Extract text from receipt image using Tesseract OCR."""
    img = Image.open(image_path)
    
    # Preprocess: convert to grayscale, increase contrast
    img = img.convert('L')
    
    # Run OCR
    text = pytesseract.image_to_string(img, lang=OCR_LANGUAGES)
    
    # Parse extracted text
    data = parse_receipt_text(text)
    data['raw_text'] = text
    
    return data


def parse_receipt_text(text):
    """Try to extract structured data from OCR text."""
    lines = text.strip().split('\n')
    
    result = {
        'supplier': '',
        'date': '',
        'total': '',
        'items': [],
        'lines': [l.strip() for l in lines if l.strip()]
    }
    
    # Extract total amount (look for patterns like "Total: 150.000" or "Rp 150.000")
    total_patterns = [
        r'[Tt]otal\s*[:\.]?\s*(?:Rp\.?\s*)?([\d.,]+)',
        r'(?:Rp\.?\s*)([\d.,]+)\s*(?:total|TOTAL)',
        r'[Gg]rand\s*[Tt]otal\s*[:\.]?\s*(?:Rp\.?\s*)?([\d.,]+)',
        r'JUMLAH\s*[:\.]?\s*(?:Rp\.?\s*)?([\d.,]+)',
        r'[Jj]umlah\s*[:\.]?\s*(?:Rp\.?\s*)?([\d.,]+)',
    ]
    for pattern in total_patterns:
        match = re.search(pattern, text)
        if match:
            result['total'] = match.group(1).strip()
            break
    
    # Extract date
    date_patterns = [
        r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        r'(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            result['date'] = match.group(1).strip()
            break
    
    # First non-empty line is often the store/supplier name
    for line in lines:
        line = line.strip()
        if line and len(line) > 2:
            result['supplier'] = line
            break
    
    return result


# ─── Routes ──────────────────────────────────────────────────────────
@app.route('/')
def index():
    """Mobile-friendly upload page."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/upload', methods=['POST'])
def upload():
    """Handle receipt upload and OCR."""
    if 'receipt' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['receipt']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save file
    ext = os.path.splitext(file.filename)[1] or '.jpg'
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Run OCR
    try:
        data = extract_receipt_data(filepath)
        data['filename'] = filename
        
        # Get Odoo accounts for selection
        _, models, uid = odoo_connect()
        
        # Get expense accounts
        accounts = odoo_search_read(
            models, uid, 'account.account',
            domain=[['user_type_id.name', 'in', ['Expenses', 'Income', 'Cost of Revenue']]],
            fields=['code', 'name', 'user_type_id'],
            limit=30
        )
        
        # Get products for COGS selection
        products = odoo_search_read(
            models, uid, 'product.product',
            domain=[['purchase_ok', '=', True]],
            fields=['name', 'default_code', 'list_price'],
            limit=30
        )
        
        # Get suppliers
        suppliers = odoo_search_read(
            models, uid, 'res.partner',
            domain=[['supplier', '=', True]],
            fields=['name'],
            limit=20
        )
        
        return jsonify({
            'success': True,
            'ocr': data,
            'accounts': accounts,
            'products': products,
            'suppliers': suppliers,
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/submit', methods=['POST'])
def submit():
    """Create expense or COGS entry in Odoo."""
    try:
        data = request.json
        entry_type = data.get('type')  # 'expense' or 'cogs'
        
        _, models, uid = odoo_connect()
        
        supplier_name = data.get('supplier', '').strip()
        amount = data.get('amount', '0')
        description = data.get('description', '')
        account_id = data.get('account_id')
        product_id = data.get('product_id')
        filename = data.get('filename', '')
        
        # Parse amount (handle Indonesian formatting: 1.500.000 or 1,500,000)
        amount_clean = amount.replace('.', '').replace(',', '.')
        try:
            amount_float = float(amount_clean)
        except ValueError:
            return jsonify({'error': f'Invalid amount: {amount}'}), 400
        
        # Find or create supplier
        partner_id = None
        if supplier_name:
            partners = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'res.partner', 'search',
                [[['name', '=', supplier_name]]]
            )
            if partners:
                partner_id = partners[0]
            else:
                partner_id = odoo_create(models, uid, 'res.partner', {
                    'name': supplier_name,
                    'supplier': True,
                    'is_company': True
                })
        
        if not partner_id:
            # Create unknown supplier
            partner_id = odoo_create(models, uid, 'res.partner', {
                'name': supplier_name or 'Unknown Supplier',
                'supplier': True,
                'is_company': True
            })
        
        # Read attachment if exists
        attachment_data = None
        if filename:
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    attachment_data = base64.b64encode(f.read()).decode('utf-8')
        
        if entry_type == 'expense':
            # Create vendor bill (account.move type='in_invoice')
            move_vals = {
                'type': 'in_invoice',
                'partner_id': partner_id,
                'invoice_date': datetime.now().strftime('%Y-%m-%d'),
                'ref': description or 'Receipt scan',
                'invoice_line_ids': [(0, 0, {
                    'name': description or 'Receipt expense',
                    'quantity': 1,
                    'price_unit': amount_float,
                    'account_id': int(account_id) if account_id else None,
                })]
            }
            
            move_id = odoo_create(models, uid, 'account.move', move_vals)
            
            # Attach receipt image
            if attachment_data:
                odoo_create(models, uid, 'ir.attachment', {
                    'name': f'receipt_{filename}',
                    'datas': attachment_data,
                    'res_model': 'account.move',
                    'res_id': move_id,
                    'mimetype': 'image/jpeg',
                })
            
            return jsonify({
                'success': True,
                'type': 'expense',
                'record_id': move_id,
                'model': 'account.move',
                'message': f'Expense vendor bill created (ID: {move_id})'
            })
            
        elif entry_type == 'cogs':
            # Create vendor bill for inventory purchase
            # You can later link this to stock moves manually
            if not product_id:
                return jsonify({'error': 'Product required for COGS'}), 400
            
            move_vals = {
                'type': 'in_invoice',
                'partner_id': partner_id,
                'invoice_date': datetime.now().strftime('%Y-%m-%d'),
                'ref': f'[COGS] {description or "Receipt scan"}',
                'invoice_line_ids': [(0, 0, {
                    'name': description or 'Inventory purchase',
                    'quantity': 1,
                    'price_unit': amount_float,
                    'product_id': int(product_id),
                })]
            }
            
            move_id = odoo_create(models, uid, 'account.move', move_vals)
            
            # Attach receipt
            if attachment_data:
                odoo_create(models, uid, 'ir.attachment', {
                    'name': f'receipt_{filename}',
                    'datas': attachment_data,
                    'res_model': 'account.move',
                    'res_id': move_id,
                    'mimetype': 'image/jpeg',
                })
            
            return jsonify({
                'success': True,
                'type': 'cogs',
                'record_id': move_id,
                'model': 'account.move',
                'message': f'COGS vendor bill created (ID: {move_id})'
            })
        
        else:
            return jsonify({'error': 'Invalid type. Use "expense" or "cogs"'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/test-odoo')
def test_odoo():
    """Test Odoo connection."""
    try:
        common, models, uid = odoo_connect()
        
        # Get some info
        user_info = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.users', 'read', [uid], {'fields': ['name', 'login']}
        )
        
        companies = odoo_search_read(models, uid, 'res.company', fields=['name'])
        accounts_count = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'account.account', 'search_count', [[]]
        )
        products_count = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'product.product', 'search_count', [[]]
        )
        
        return jsonify({
            'connected': True,
            'user': user_info[0] if user_info else {},
            'companies': companies,
            'accounts_count': accounts_count,
            'products_count': products_count,
            'odoo_version': common.version()
        })
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})


# ─── HTML Template ──────────────────────────────────────────────────
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>📸 Receipt Scanner - Odoo 13</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a; color: #e2e8f0;
            min-height: 100vh; padding: 16px;
        }
        .container { max-width: 480px; margin: 0 auto; }
        h1 { font-size: 1.5rem; margin-bottom: 8px; color: #38bdf8; }
        .subtitle { color: #94a3b8; font-size: 0.85rem; margin-bottom: 20px; }
        
        /* Upload Area */
        .upload-area {
            border: 2px dashed #334155; border-radius: 16px;
            padding: 40px 20px; text-align: center;
            cursor: pointer; transition: all 0.3s;
            background: #1e293b; margin-bottom: 20px;
        }
        .upload-area:hover, .upload-area.dragover {
            border-color: #38bdf8; background: #1e3a5f;
        }
        .upload-area .icon { font-size: 48px; margin-bottom: 12px; }
        .upload-area p { color: #94a3b8; }
        .upload-area input { display: none; }
        
        /* Preview */
        #preview { display: none; margin-bottom: 20px; text-align: center; }
        #preview img { max-width: 100%; border-radius: 12px; max-height: 300px; object-fit: contain; }
        
        /* Loading */
        .loading { display: none; text-align: center; padding: 40px; }
        .spinner {
            width: 40px; height: 40px; margin: 0 auto 16px;
            border: 3px solid #334155; border-top-color: #38bdf8;
            border-radius: 50%; animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        /* Results */
        #results { display: none; }
        .card {
            background: #1e293b; border-radius: 12px;
            padding: 16px; margin-bottom: 16px;
        }
        .card h3 { color: #38bdf8; font-size: 0.95rem; margin-bottom: 12px; }
        
        label { display: block; color: #94a3b8; font-size: 0.8rem; margin-bottom: 4px; margin-top: 12px; }
        input, select, textarea {
            width: 100%; padding: 10px 12px;
            background: #0f172a; border: 1px solid #334155;
            border-radius: 8px; color: #e2e8f0; font-size: 1rem;
        }
        input:focus, select:focus, textarea:focus {
            outline: none; border-color: #38bdf8;
        }
        textarea { resize: vertical; min-height: 60px; }
        
        /* Type Selection */
        .type-buttons { display: flex; gap: 12px; margin-top: 16px; }
        .type-btn {
            flex: 1; padding: 16px; border: 2px solid #334155;
            border-radius: 12px; background: #0f172a;
            color: #e2e8f0; font-size: 1rem; cursor: pointer;
            text-align: center; transition: all 0.3s;
        }
        .type-btn:hover { border-color: #38bdf8; }
        .type-btn.selected { border-color: #38bdf8; background: #1e3a5f; }
        .type-btn .emoji { font-size: 24px; display: block; margin-bottom: 6px; }
        .type-btn .label { font-size: 0.85rem; color: #94a3b8; }
        
        /* Submit */
        .submit-btn {
            width: 100%; padding: 14px; margin-top: 20px;
            background: linear-gradient(135deg, #0ea5e9, #2563eb);
            border: none; border-radius: 12px;
            color: white; font-size: 1.1rem; font-weight: 600;
            cursor: pointer; transition: opacity 0.3s;
        }
        .submit-btn:hover { opacity: 0.9; }
        .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        /* COGS fields */
        #cogs-fields { display: none; }
        
        /* Raw text */
        .raw-text {
            background: #0f172a; border-radius: 8px;
            padding: 12px; font-family: monospace;
            font-size: 0.75rem; color: #94a3b8;
            max-height: 150px; overflow-y: auto;
            white-space: pre-wrap; margin-top: 8px;
        }
        
        /* Status */
        .status { padding: 12px; border-radius: 8px; margin-top: 16px; display: none; }
        .status.success { background: #064e3b; color: #6ee7b7; display: block; }
        .status.error { background: #7f1d1d; color: #fca5a5; display: block; }
        
        /* Test link */
        .test-link { text-align: center; margin-top: 20px; }
        .test-link a { color: #38bdf8; text-decoration: none; font-size: 0.85rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📸 Receipt Scanner</h1>
        <p class="subtitle">Odoo 13 · Toko Makmur</p>
        
        <!-- Upload -->
        <div class="upload-area" id="uploadArea" onclick="document.getElementById('fileInput').click()">
            <div class="icon">📷</div>
            <p>Tap to scan receipt</p>
            <p style="font-size:0.75rem;margin-top:8px">or drag & drop image</p>
            <input type="file" id="fileInput" accept="image/*" capture="environment">
        </div>
        
        <!-- Preview -->
        <div id="preview">
            <img id="previewImg" src="" alt="Receipt">
        </div>
        
        <!-- Loading -->
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Reading receipt...</p>
        </div>
        
        <!-- Results -->
        <div id="results">
            <!-- OCR Results -->
            <div class="card">
                <h3>📝 Extracted Data</h3>
                
                <label>Supplier / Toko</label>
                <input type="text" id="supplier" placeholder="Nama toko">
                
                <label>Total Amount (Rp)</label>
                <input type="text" id="amount" placeholder="0">
                
                <label>Description</label>
                <textarea id="description" placeholder="Keterangan"></textarea>
                
                <details style="margin-top:12px">
                    <summary style="color:#94a3b8;font-size:0.8rem;cursor:pointer">Show raw OCR text</summary>
                    <div class="raw-text" id="rawText"></div>
                </details>
            </div>
            
            <!-- Type Selection -->
            <div class="card">
                <h3>📊 Entry Type</h3>
                <div class="type-buttons">
                    <button class="type-btn" onclick="selectType('expense')" id="btn-expense">
                        <span class="emoji">💰</span>
                        Expense
                        <div class="label">Biaya operasional</div>
                    </button>
                    <button class="type-btn" onclick="selectType('cogs')" id="btn-cogs">
                        <span class="emoji">📦</span>
                        COGS
                        <div class="label">Stok / Inventory</div>
                    </button>
                </div>
            </div>
            
            <!-- Expense Account -->
            <div class="card" id="expense-fields">
                <h3>💰 Expense Account</h3>
                <label>Account</label>
                <select id="account_id">
                    <option value="">-- Select account --</option>
                </select>
            </div>
            
            <!-- COGS Fields -->
            <div class="card" id="cogs-fields">
                <h3>📦 Inventory Details</h3>
                <label>Product</label>
                <select id="product_id">
                    <option value="">-- Select product --</option>
                </select>
            </div>
            
            <!-- Submit -->
            <button class="submit-btn" id="submitBtn" onclick="submitEntry()">
                ✅ Save to Odoo
            </button>
            
            <div class="status" id="status"></div>
            
            <!-- New Scan -->
            <div style="text-align:center;margin-top:16px">
                <a href="/" style="color:#38bdf8;text-decoration:none;font-size:0.9rem">📸 Scan another</a>
            </div>
        </div>
        
        <div class="test-link">
            <a href="/test-odoo" target="_blank">🔧 Test Odoo Connection</a>
        </div>
    </div>

    <script>
        let selectedType = null;
        let ocrData = null;
        let currentFilename = null;

        // Drag & drop
        const uploadArea = document.getElementById('uploadArea');
        uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
        uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
        });

        document.getElementById('fileInput').addEventListener('change', (e) => {
            if (e.target.files.length) handleFile(e.target.files[0]);
        });

        function handleFile(file) {
            // Preview
            const reader = new FileReader();
            reader.onload = (e) => {
                document.getElementById('previewImg').src = e.target.result;
                document.getElementById('preview').style.display = 'block';
            };
            reader.readAsDataURL(file);
            
            // Upload
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            
            const formData = new FormData();
            formData.append('receipt', file);
            
            fetch('/upload', { method: 'POST', body: formData })
                .then(r => r.json())
                .then(data => {
                    document.getElementById('loading').style.display = 'none';
                    if (data.error) {
                        showError(data.error);
                        return;
                    }
                    showResults(data);
                })
                .catch(err => {
                    document.getElementById('loading').style.display = 'none';
                    showError('Upload failed: ' + err.message);
                });
        }

        function showResults(data) {
            ocrData = data.ocr;
            currentFilename = data.filename;
            
            // Fill OCR data
            document.getElementById('supplier').value = ocrData.supplier || '';
            document.getElementById('amount').value = ocrData.total || '';
            document.getElementById('description').value = '';
            document.getElementById('rawText').textContent = ocrData.raw_text || '';
            
            // Fill accounts
            const accountSelect = document.getElementById('account_id');
            accountSelect.innerHTML = '<option value="">-- Select account --</option>';
            (data.accounts || []).forEach(a => {
                accountSelect.innerHTML += `<option value="${a.id}">${a.code} - ${a.name}</option>`;
            });
            
            // Fill products
            const productSelect = document.getElementById('product_id');
            productSelect.innerHTML = '<option value="">-- Select product --</option>';
            (data.products || []).forEach(p => {
                productSelect.innerHTML += `<option value="${p.id}">${p.default_code ? p.default_code + ' - ' : ''}${p.name}</option>`;
            });
            
            document.getElementById('results').style.display = 'block';
        }

        function selectType(type) {
            selectedType = type;
            document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('selected'));
            document.getElementById('btn-' + type).classList.add('selected');
            document.getElementById('expense-fields').style.display = type === 'expense' ? 'block' : 'none';
            document.getElementById('cogs-fields').style.display = type === 'cogs' ? 'block' : 'none';
        }

        function submitEntry() {
            if (!selectedType) {
                showError('Pilih tipe: Expense atau COGS');
                return;
            }
            
            const btn = document.getElementById('submitBtn');
            btn.disabled = true;
            btn.textContent = '⏳ Saving...';
            
            const payload = {
                type: selectedType,
                supplier: document.getElementById('supplier').value,
                amount: document.getElementById('amount').value,
                description: document.getElementById('description').value,
                account_id: document.getElementById('account_id').value || null,
                product_id: document.getElementById('product_id').value || null,
                filename: currentFilename
            };
            
            fetch('/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(r => r.json())
            .then(data => {
                btn.disabled = false;
                btn.textContent = '✅ Save to Odoo';
                if (data.success) {
                    const status = document.getElementById('status');
                    status.className = 'status success';
                    status.textContent = `✅ ${data.message}`;
                } else {
                    showError(data.error);
                }
            })
            .catch(err => {
                btn.disabled = false;
                btn.textContent = '✅ Save to Odoo';
                showError('Submit failed: ' + err.message);
            });
        }

        function showError(msg) {
            const status = document.getElementById('status');
            status.className = 'status error';
            status.textContent = '❌ ' + msg;
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("🚀 Receipt Scanner starting...")
    print(f"📡 Odoo: {ODOO_URL} / DB: {ODOO_DB}")
    print(f"🌐 Open: http://0.0.0.0:5000")
    print(f"📱 Phone: http://<your-ip>:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
