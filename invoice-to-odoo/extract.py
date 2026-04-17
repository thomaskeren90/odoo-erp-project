#!/usr/bin/env python3
"""
Extract invoice/receipt data from images using Ollama Vision.
Supports llava, minicpm-v, llama3.2-vision, or any vision model in Ollama.
"""

import os
import json
import base64
import logging
import requests

log = logging.getLogger("invoice-to-odoo")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llava")
EXTRACTION_PROMPT = os.getenv("EXTRACTION_PROMPT", "").strip()

DEFAULT_PROMPT = """You are an invoice and receipt data extraction AI.
Analyze this image and extract ALL information into a JSON object.

Return ONLY valid JSON, no markdown, no explanation. Use this exact structure:

{
  "supplier_name": "name of vendor/supplier",
  "supplier_vat": "tax ID if visible, else null",
  "invoice_number": "invoice/receipt number",
  "invoice_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD or null",
  "currency": "USD/EUR/GBP/THB/IDR etc",
  "subtotal": 0.0,
  "tax_amount": 0.0,
  "total_amount": 0.0,
  "line_items": [
    {
      "description": "item description",
      "quantity": 1.0,
      "unit_price": 0.0,
      "tax_rate": 0.0,
      "total": 0.0
    }
  ],
  "payment_method": "cash/card/transfer/null",
  "notes": "any other relevant info",
  "document_type": "invoice|receipt|delivery_note|expense"
}

Rules:
- Use null for missing fields, not empty string
- Numbers must be actual numbers, not strings
- If you can't read something, use null
- line_items can be empty array if nothing itemized
- Be precise with numbers — no currency symbols in values"""


def encode_image(image_path: str) -> str:
    """Read and base64-encode an image."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_invoice_data(image_path: str) -> dict | None:
    """
    Send image to Ollama vision model and extract structured data.
    Returns dict with invoice fields or None on failure.
    """
    prompt = EXTRACTION_PROMPT if EXTRACTION_PROMPT else DEFAULT_PROMPT

    log.info(f"  Model: {OLLAMA_MODEL} @ {OLLAMA_URL}")

    # Encode image
    b64 = encode_image(image_path)

    # Call Ollama
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "images": [b64],
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temp for accuracy
                    "num_predict": 2048,
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        log.error("  ❌ Cannot connect to Ollama. Is it running? (ollama serve)")
        return None
    except requests.exceptions.Timeout:
        log.error("  ❌ Ollama timed out (120s). Try a smaller model.")
        return None

    result = resp.json()
    raw = result.get("response", "").strip()

    # Parse JSON from response
    # Sometimes the model wraps in ```json ... ```
    text = raw
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        data = json.loads(text.strip())
        log.info(f"  ✅ Extracted: {data.get('supplier_name', '?')} — "
                 f"total: {data.get('total_amount', '?')}")
        return data
    except json.JSONDecodeError as e:
        log.error(f"  ❌ Failed to parse JSON from model output: {e}")
        log.debug(f"  Raw output: {raw[:500]}")
        return None


if __name__ == "__main__":
    # Test extraction standalone
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract.py <image_path>")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO)
    data = extract_invoice_data(sys.argv[1])
    if data:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("Extraction failed.")
