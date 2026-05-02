import google.generativeai as genai
import PIL.Image

genai.configure(api_key="AIzaSyAbNFQqmn0UxHOgT7Tg-3lEhTXSr9rfB_Y")

model = genai.GenerativeModel("gemini-2.5-flash")


image = PIL.Image.open("/mnt/c/Users/kusum/Downloads/WhatsApp Image 2026-04-17 at 20.05.17.jpeg")

prompt = """
You are an invoice OCR assistant. Look at this invoice image carefully.
Extract the data and return ONLY valid JSON, no explanation, no markdown.
Use this exact structure:
{
  "supplier": "",
  "invoice_number": "",
  "date": "",
  "type": "invoice or expense",
  "lines": [
    {"description": "", "qty": 0, "unit_price": 0, "total": 0}
  ],
  "subtotal": 0,
  "tax": 0,
  "total": 0,
  "currency": "IDR"
}
If a field is not visible, use null.
"""

response = model.generate_content([prompt, image])
print(response.text)
