"""
Odoo 13 Receipt Scanner Configuration
=======================================
Copy to config.py and fill in your values:

  cp config_example.py config.py
"""

# ODOO 13 CONNECTION
ODOO_URL = "http://localhost:8069"
ODOO_DB = "your_database_name"
ODOO_USERNAME = "admin"
ODOO_PASSWORD = "your_password"

# AI VISION CONFIG
# Option 1: Ollama (local) - pull a vision model first:
#   docker exec ollama_brain ollama pull llava:phi3
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llava:phi3"

# Option 2: OpenAI GPT-4o-mini (~$0.001/receipt)
OPENAI_API_KEY = ""
OPENAI_MODEL = "gpt-4o-mini"

# Option 3: Google Gemini Flash (free tier)
GEMINI_API_KEY = ""

# Primary AI: "ollama", "openai", or "gemini"
AI_PROVIDER = "ollama"

# APP SETTINGS
UPLOAD_FOLDER = "/tmp/receipts"
HOST = "0.0.0.0"
PORT = 5000
