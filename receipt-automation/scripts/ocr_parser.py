#!/usr/bin/env python3
"""
OCR Receipt Parser — Uses Ollama Vision to extract structured data from receipt images.
Run: python3 ocr_parser.py <image_path>
Output: JSON to stdout
"""
import sys
import json
import base64
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llava"  # or llava:13b, bakllava, etc. — whatever you have pulled

EXTRACT_PROMPT = """Analyze this receipt/invoice image and extract the following into valid JSON only (no markdown, no explanation):

{
  "vendor": "company or shop name",
  "date": "YYYY-MM-DD or null if not visible",
  "total_amount": 0.0,
  "currency": "IDR",
  "tax_amount": 0.0,
  "line_items": [
    {"description": "item name", "quantity": 1, "unit_price": 0.0, "subtotal": 0.0}
  ],
  "receipt_number": "invoice/receipt number or null",
  "is_readable": true
}

Rules:
- If the image is not a receipt/invoice, set is_readable to false
- currency defaults to IDR for Indonesian receipts
- Be precise with numbers — no rounding
- Return ONLY the JSON object, nothing else"""


def parse_receipt(image_path: str) -> dict:
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "model": MODEL,
        "prompt": EXTRACT_PROMPT,
        "images": [image_b64],
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()

    response_text = resp.json().get("response", "").strip()

    # Try to extract JSON from response (handle markdown wrapping)
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]

    return json.loads(response_text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ocr_parser.py <image_path>", file=sys.stderr)
        sys.exit(1)

    result = parse_receipt(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
