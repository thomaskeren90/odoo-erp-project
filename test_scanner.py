"""
Diagnostic - run: python3 test_scanner.py
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

test("Flask", lambda: __import__('flask').__version__)

def check_ollama():
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    models = [m['name'] for m in r.json().get('models', [])]
    return f"Running. Models: {models}"
test("Ollama", check_ollama)

def check_odoo():
    r = requests.post("http://localhost:8069/web/database/list",
        headers={"Content-Type": "application/json"},
        data='{"jsonrpc":"2.0","method":"call","params":{},"id":1}',
        timeout=5)
    return f"Responding (status {r.status_code})"
test("Odoo 13", check_odoo)

# Test AI with detailed output
def test_ai():
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (400, 200), 'white')
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "TOKO MAKMUR", fill='black')
    draw.text((20, 50), "Total: Rp 150.000", fill='black')
    draw.text((20, 80), "Date: 06/04/2026", fill='black')
    test_path = "/tmp/test_receipt.png"
    img.save(test_path)

    with open(test_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    # Try both models
    for model in ["gemma3:1b", "qwen3.5:0.8b"]:
        print(f"\n  Testing model: {model}")
        try:
            r = requests.post("http://localhost:11434/api/generate", json={
                "model": model,
                "prompt": "What text do you see in this image? Answer in one sentence.",
                "images": [b64],
                "stream": False,
                "options": {"temperature": 0}
            }, timeout=60)

            result = r.json()
            print(f"    Status: {r.status_code}")
            print(f"    Keys: {list(result.keys())}")
            resp = result.get("response", "")
            print(f"    Response length: {len(resp)}")
            print(f"    Response: {resp[:300] if resp else 'EMPTY'}")
            if result.get("error"):
                print(f"    Error: {result['error']}")
        except Exception as e:
            print(f"    Failed: {e}")

    return "Done - check output above"

test("AI Vision", test_ai)

print("\n=== Done ===")
