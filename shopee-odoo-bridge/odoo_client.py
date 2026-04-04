"""
Odoo 13 XML-RPC Client
=======================
Handles all communication with Odoo 13 via XML-RPC.
Creates invoices, payments, journal entries, etc.
"""

import xmlrpc.client
import os
from datetime import datetime

try:
    from config import ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, ACCOUNT_MAP, JOURNAL_MAP
except ImportError:
    ODOO_URL = os.environ.get("ODOO_URL", "http://localhost:8069")
    ODOO_DB = os.environ.get("ODOO_DB", "tokoodoo13")
    ODOO_USERNAME = os.environ.get("ODOO_USERNAME", "tokomakmur")
    ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin123")
    ACCOUNT_MAP = {}
    JOURNAL_MAP = {}


class OdooClient:
    def __init__(self):
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.username = ODOO_USERNAME
        self.password = ODOO_PASSWORD
        self.uid = None
        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def connect(self):
        """Authenticate and get user ID."""
        version = self.common.version()
        print(f"Odoo {version.get('server_version', '?')} connected")
        self.uid = self.common.authenticate(self.db, self.username, self.password, {})
        if not self.uid:
            raise Exception("Authentication failed for Odoo")
        print(f"Authenticated as uid={self.uid}")
        return self.uid

    def _search(self, model, domain):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, "search", [domain]
        )

    def _read(self, model, ids, fields=None):
        kwargs = {}
        if fields:
            kwargs["fields"] = fields
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, "read", [ids], kwargs
        )

    def _create(self, model, values):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, "create", [values]
        )

    def _write(self, model, ids, values):
        if not isinstance(ids, list):
            ids = [ids]
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, "write", [ids, values]
        )

    # ==========================================
    # ACCOUNT LOOKUPS
    # ==========================================
    def get_account_id(self, code):
        """Find account ID by code from config mapping."""
        mapped_code = ACCOUNT_MAP.get(code, code)
        ids = self._search("account.account", [("code", "=", mapped_code)])
        return ids[0] if ids else None

    def get_journal_id(self, code):
        """Find journal ID by code from config mapping."""
        mapped_code = JOURNAL_MAP.get(code, code)
        ids = self._search("account.journal", [("code", "=", mapped_code)])
        return ids[0] if ids else None

    def get_partner_id(self, name, is_customer=True):
        """Find or create partner."""
        ids = self._search("res.partner", [("name", "=", name)])
        if ids:
            return ids[0]
        # Create new partner
        values = {"name": name, "customer": is_customer, "supplier": not is_customer}
        return self._create("res.partner", values)

    # ==========================================
    # INVOICES (account.move)
    # ==========================================
    def create_customer_invoice(self, partner_name, order_ref, lines, invoice_date=None, journal_code="SALES"):
        """Create a customer invoice (out_invoice).
        
        lines: list of dicts with keys: name, quantity, price_unit, account_code
        """
        partner_id = self.get_partner_id(partner_name, is_customer=True)
        if not partner_id:
            raise Exception(f"Could not find/create partner: {partner_name}")

        journal_id = self.get_journal_id(journal_code)
        account_receivable = self.get_account_id("ar_marketplace")  # 112002

        if not invoice_date:
            invoice_date = datetime.now().strftime("%Y-%m-%d")

        invoice_lines = []
        for line in lines:
            account_id = self.get_account_id(line["account_code"])
            invoice_lines.append((0, 0, {
                "name": line["name"],
                "quantity": line.get("quantity", 1),
                "price_unit": line.get("price_unit", 0),
                "account_id": account_id,
            }))

        invoice_data = {
            "partner_id": partner_id,
            "type": "out_invoice",
            "invoice_date": invoice_date,
            "date": invoice_date,
            "ref": order_ref,
            "journal_id": journal_id,
            "invoice_line_ids": invoice_lines,
        }

        invoice_id = self._create("account.move", invoice_data)
        print(f"✅ Invoice created: {order_ref} (id={invoice_id})")
        return invoice_id

    def create_vendor_bill(self, partner_name, ref, lines, bill_date=None):
        """Create a vendor bill (in_invoice)."""
        partner_id = self.get_partner_id(partner_name, is_customer=False)
        journal_id = self.get_journal_id("PURCH")

        if not bill_date:
            bill_date = datetime.now().strftime("%Y-%m-%d")

        invoice_lines = []
        for line in lines:
            account_id = self.get_account_id(line["account_code"])
            invoice_lines.append((0, 0, {
                "name": line["name"],
                "quantity": line.get("quantity", 1),
                "price_unit": line.get("price_unit", 0),
                "account_id": account_id,
            }))

        bill_data = {
            "partner_id": partner_id,
            "type": "in_invoice",
            "invoice_date": bill_date,
            "date": bill_date,
            "ref": ref,
            "journal_id": journal_id,
            "invoice_line_ids": invoice_lines,
        }

        bill_id = self._create("account.move", bill_data)
        print(f"✅ Vendor bill created: {ref} (id={bill_id})")
        return bill_id

    # ==========================================
    # JOURNAL ENTRIES
    # ==========================================
    def create_journal_entry(self, ref, lines, date=None, journal_code="EXP"):
        """Create a manual journal entry.
        
        lines: list of dicts with keys: name, debit, credit, account_code
        """
        journal_id = self.get_journal_id(journal_code)
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        move_lines = []
        for line in lines:
            account_id = self.get_account_id(line["account_code"])
            move_lines.append((0, 0, {
                "name": line["name"],
                "debit": line.get("debit", 0),
                "credit": line.get("credit", 0),
                "account_id": account_id,
            }))

        entry_data = {
            "ref": ref,
            "journal_id": journal_id,
            "date": date,
            "line_ids": move_lines,
        }

        entry_id = self._create("account.move", entry_data)
        print(f"✅ Journal entry created: {ref} (id={entry_id})")
        return entry_id

    # ==========================================
    # SHOPEE-SPECIFIC RECORDS
    # ==========================================
    def record_shopee_order(self, order_data):
        """Record a Shopee order as a customer invoice.
        
        order_data: {
            "order_sn": "230401XXXXX",
            "buyer_username": "buyer123",
            "total_amount": 150000,
            "shipping_fee": 0,
            "actual_shipping_fee": 15000,
            "items": [{"name": "Mesin Jahit Singer", "qty": 1, "price": 150000}],
            "order_date": "2026-04-01",
            "platform_fee": 7500,       # Shopee commission
            "service_fee": 2250,        # payment fee
        }
        """
        lines = []
        for item in order_data["items"]:
            lines.append({
                "name": item["name"],
                "quantity": item["qty"],
                "price_unit": item["price"],
                "account_code": "ecommerce_sales",
            })

        return self.create_customer_invoice(
            partner_name=f"Shopee: {order_data['buyer_username']}",
            order_ref=f"SHOPEE-{order_data['order_sn']}",
            lines=lines,
            invoice_date=order_data.get("order_date"),
        )

    def record_shopee_disbursement(self, disbursement_data):
        """Record Shopee payment received into SeaBank.
        
        disbursement_data: {
            "transaction_id": "T230401XXXX",
            "amount": 125000,
            "date": "2026-04-03",
            "order_sns": ["230401XXXXX"],
        }
        """
        seabank_id = self.get_account_id("seabank")
        ar_marketplace_id = self.get_account_id("ar_marketplace")
        ref = f"SHOPEE-PAY-{disbursement_data['transaction_id']}"
        date = disbursement_data.get("date", datetime.now().strftime("%Y-%m-%d"))

        lines = [
            {"name": ref, "debit": disbursement_data["amount"], "credit": 0, "account_code": "seabank"},
            {"name": ref, "debit": 0, "credit": disbursement_data["amount"], "account_code": "ar_marketplace"},
        ]

        return self.create_journal_entry(ref, lines, date=date, journal_code="SEAB")

    def record_shopee_fees(self, order_sn, fees, date=None):
        """Record Shopee platform fees (commission + payment fee).
        
        fees: [{"type": "commission", "amount": 7500}, {"type": "payment_fee", "amount": 2250}]
        """
        lines = []
        total_fee = 0
        for fee in fees:
            total_fee += fee["amount"]
            lines.append({
                "name": f"Shopee {fee['type']} - {order_sn}",
                "debit": fee["amount"],
                "credit": 0,
                "account_code": "marketplace_fee",
            })

        lines.append({
            "name": f"Shopee fees - {order_sn}",
            "debit": 0,
            "credit": total_fee,
            "account_code": "ar_marketplace",
        })

        ref = f"SHOPEE-FEE-{order_sn}"
        return self.create_journal_entry(ref, lines, date=date)

    def record_shopee_return(self, order_sn, refund_amount, date=None):
        """Record a Shopee return/refund."""
        lines = [
            {"name": f"Return - {order_sn}", "debit": refund_amount, "credit": 0, "account_code": "returns_refund"},
            {"name": f"Return - {order_sn}", "debit": 0, "credit": refund_amount, "account_code": "ar_marketplace"},
        ]
        ref = f"SHOPEE-RET-{order_sn}"
        return self.create_journal_entry(ref, lines, date=date)


def test_connection():
    """Test Odoo connection."""
    client = OdooClient()
    try:
        client.connect()

        # Check accounts exist
        for code_name, code_num in ACCOUNT_MAP.items():
            acc_id = client.get_account_id(code_name)
            status = "✅" if acc_id else "❌"
            print(f"  {status} {code_name} ({code_num}): id={acc_id}")

        # Check journals exist
        for code_name, code_num in JOURNAL_MAP.items():
            j_id = client.get_journal_id(code_name)
            status = "✅" if j_id else "❌"
            print(f"  {status} {code_name} ({code_num}): id={j_id}")

        return True
    except Exception as e:
        print(f"❌ Odoo connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
