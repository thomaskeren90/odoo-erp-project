"""
Quick test - does each step work?
Run this first: python3 test_scanner.py
"""
import os
import sys
import requests
import json
import base64

def test(step, fn):
    try:
        result = fn()
        print(f"  ✅ {step}: {result}")
        return True
    except Exception as e:
        print(f"  ❌ {step}: {e}")
        return False

print("=== Receipt Scanner Diagnostics ===\n")

# 1. Check Flask
test("Flask", lambda: __import__('flask').__version__)

# 2. Check Ollama
def check_ollama():
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    models = [m['name'] for m in r.json().get('models', [])]
    return f"Running. Models: {models}"
test("Ollama", check_ollama)

# 3. Check Ollama vision model
def check_vision():
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    models = [m['name'] for m in r.json().get('models', [])]
    vision = [m for m in models if any(v in m for v in ['gemma', 'llava', 'vision', 'qwen3.5', 'minicpm'])]
    if not vision:
        return f"No vision models found. Have: {models}"
    return f"Vision models: {vision}"
test("Vision models", check_vision)

# 4. Check Odoo
def check_odoo():
    r = requests.get("http://localhost:8069/web/database/list", 
                      headers={"Content-Type": "application/json"},
                      data='{"jsonrpc":"2.0","method":"call","params":{},"id":1}',
                      timeout=5)
    return f"Odoo responding (status {r.status_code})"
test("Odoo 13", check_odoo)

# 5. Test AI extraction with a dummy image
def test_ai():
    # Create a tiny test image with text
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (400, 200), 'white')
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "TOKO MAKMUR", fill='black')
    draw.text((20, 50), "Jl. Sudirman No. 123", fill='black')
    draw.text((20, 80), "Total: Rp 150.000", fill='black')
    draw.text((20, 110), "Date: 06/04/2026", fill='black')
    test_path = "/tmp/test_receipt.png"
    img.save(test_path)
    
    # Try Ollama
    with open(test_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    
    r = requests.post("http://localhost:11434/api/generate", json={
        "model": "gemma3:1b",
        "prompt": "Read this receipt image. Extract: supplier name, total amount, date. Return as JSON: {supplier, total, date}",
        "images": [b64],
        "stream": False,
        "options": {"temperature": 0}
    }, timeout=120)
    
    result = r.json()
    response = result.get("response", "NO RESPONSE")
    return f"AI says: {response[:200]}"

test("AI extraction", test_ai)

print("\n=== Done ===")
