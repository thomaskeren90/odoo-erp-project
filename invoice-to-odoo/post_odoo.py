#!/usr/bin/env python3
"""
Post extracted invoice data to Odoo 13 via XML-RPC.
Handles: Account Payable (Vendor Bills), Inventory, Expenses.
"""

import os
import logging
import xmlrpc.client
from datetime import datetime

log = logging.getLogger("invoice-to-odoo")


class OdooPoster:
    """Manages connection and posting to Odoo 13."""

    def __init__(self):
        self.url = os.getenv("ODOO_URL", "http://localhost:8069")
        self.db = os.getenv("ODOO_DB", "odoo")
        self.username = os.getenv("ODOO_USERNAME", "admin")
        self.password = os.getenv("ODOO_PASSWORD", "admin")

        # Optional: default accounts/codes
        self.expense_account = os.getenv("ODOO_EXPENSE_ACCOUNT", "211000")
        self.payable_account = os.getenv("ODOO_PAYABLE_ACCOUNT", "200000")
        self.receivable_account = os.getenv("ODOO_RECEIVABLE_ACCOUNT", "120000")
        self.default_tax_id = os.getenv("ODOO_DEFAULT_TAX_ID", "")

        self._uid = None

    def _connect(self):
        """Authenticate and get UID."""
        if self._uid:
            return
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self._uid = common.authenticate(self.db, self.username, self.password, {})
        if not self._uid:
            raise ConnectionError(
                f"Odoo auth failed for {self.username}@{self.db}. "
                "Check ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD in .env"
            )
        log.info(f"  🔗 Connected to Odoo (uid={self._uid})")

    def _models(self):
        """Get models proxy."""
        self._connect()
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def _execute(self, model, method, *args):
        """Execute Odoo model method."""
        models = self._models()
        return models.execute_kw(
            self.db, self._uid, self.password, model, method, *args
        )

    # ─── Partner / Supplier ───────────────────────────────────────

    def find_or_create_supplier(self, name: str, vat: str = None) -> int:
        """Find existing supplier or create new one."""
        if not name:
            raise ValueError("Supplier name is required")

        # Search by name
        partners = self._execute(
            "res.partner", "search_read",
            [[["name", "ilike", name], ["supplier", "=", True]]],
            {"fields": ["id", "name"], "limit": 1}
        )
        if partners:
            log.info(f"  👤 Found supplier: {partners[0]['name']} (id={partners[0]['id']})")
            return partners[0]["id"]

        # Create new supplier
        vals = {
            "name": name,
            "supplier": True,
            "customer": False,
            "company_type": "company",
        }
        if vat:
            vals["vat"] = vat
        partner_id = self._execute("res.partner", "create", [vals])
        log.info(f"  👤 Created supplier: {name} (id={partner_id})")
        return partner_id

    # ─── Vendor Bill (Account Payable) ────────────────────────────

    def create_vendor_bill(self, data: dict, partner_id: int) -> int:
        """
        Create a vendor bill (account.move with type='in_invoice').
        This posts to Account Payable.
        """
        invoice_date = data.get("invoice_date") or datetime.now().strftime("%Y-%m-%d")
        due_date = data.get("due_date")

        # Build invoice line items
        invoice_lines = []
        for item in data.get("line_items", []):
            line_vals = [
                0, 0, {
                    "name": item.get("description", "Item"),
                    "quantity": item.get("quantity", 1.0),
                    "price_unit": item.get("unit_price", 0.0),
                    # Tax ID from env or skip
                ]
            ]
            tax_id = self.default_tax_id
            if tax_id:
                line_vals[2]["invoice_line_tax_ids"] = [(6, 0, [int(tax_id)])]
            invoice_lines.append(line_vals)

        # If no line items, create one with total
        if not invoice_lines and data.get("total_amount"):
            invoice_lines = [
                (0, 0, {
                    "name": data.get("notes", "Invoice total"),
                    "quantity": 1.0,
                    "price_unit": float(data["total_amount"]),
                })
            ]

        bill_vals = {
            "partner_id": partner_id,
            "type": "in_invoice",
            "invoice_date": invoice_date,
            "invoice_line_ids": invoice_lines,
        }
        if due_date:
            bill_vals["invoice_date_due"] = due_date

        bill_id = self._execute("account.move", "create", [bill_vals])
        log.info(f"  📄 Created vendor bill (id={bill_id})")
        return bill_id

    # ─── Expense ──────────────────────────────────────────────────

    def create_expense(self, data: dict, partner_id: int) -> int:
        """
        Create an expense entry.
        Posts to expense account in accounting.
        """
        total = float(data.get("total_amount", 0))
        if total <= 0:
            return 0

        # Create a journal entry
        journal = self._execute(
            "account.journal", "search",
            [[["type", "=", "purchase"]]], {"limit": 1}
        )
        journal_id = journal[0] if journal else False

        move_vals = {
            "journal_id": journal_id,
            "ref": f"Expense: {data.get('supplier_name', 'Unknown')} - "
                   f"{data.get('invoice_number', 'N/A')}",
            "date": data.get("invoice_date") or datetime.now().strftime("%Y-%m-%d"),
            "line_ids": [
                # Debit: Expense
                (0, 0, {
                    "name": data.get("notes", "Expense"),
                    "debit": total,
                    "credit": 0.0,
                    "account_id": self._find_account(self.expense_account),
                }),
                # Credit: Payable
                (0, 0, {
                    "name": data.get("notes", "Expense payable"),
                    "debit": 0.0,
                    "credit": total,
                    "account_id": self._find_account(self.payable_account),
                }),
            ],
        }

        move_id = self._execute("account.move", "create", [move_vals])
        log.info(f"  💰 Created expense journal entry (id={move_id})")
        return move_id

    def _find_account(self, code: str) -> int:
        """Find account by code."""
        accounts = self._execute(
            "account.account", "search",
            [[["code", "=", code]]], {"limit": 1}
        )
        if accounts:
            return accounts[0]
        # Fallback: search by name
        accounts = self._execute(
            "account.account", "search",
            [[["name", "ilike", "expense"]]], {"limit": 1}
        )
        if accounts:
            return accounts[0]
        raise ValueError(f"Account with code {code} not found. Set ODOO_EXPENSE_ACCOUNT in .env")

    # ─── Inventory ────────────────────────────────────────────────

    def create_inventory_receipt(self, data: dict, partner_id: int) -> int | None:
        """
        If line items exist, create an inventory receipt (stock picking).
        Posts to Inventory module.
        """
        line_items = data.get("line_items", [])
        if not line_items:
            log.info("  📦 No line items — skipping inventory receipt")
            return None

        # Find or create products for each line item
        picking_lines = []
        for item in line_items:
            product_id = self._find_or_create_product(item.get("description", "Unknown"))
            qty = item.get("quantity", 1.0)
            picking_lines.append((0, 0, {
                "product_id": product_id,
                "product_uom_qty": qty,
                "name": item.get("description", "Item"),
            }))

        # Find incoming picking type
        picking_type = self._execute(
            "stock.picking.type", "search_read",
            [[["code", "=", "incoming"]]],
            {"fields": ["id"], "limit": 1}
        )
        picking_type_id = picking_type[0]["id"] if picking_type else False

        picking_vals = {
            "partner_id": partner_id,
            "picking_type_id": picking_type_id,
            "move_ids_without_package": picking_lines,
            "origin": f"Invoice: {data.get('invoice_number', 'N/A')}",
        }

        picking_id = self._execute("stock.picking", "create", [picking_vals])
        log.info(f"  📦 Created inventory receipt (id={picking_id})")
        return picking_id

    def _find_or_create_product(self, name: str) -> int:
        """Find product by name or create a storable one."""
        products = self._execute(
            "product.product", "search",
            [[["name", "ilike", name]]], {"limit": 1}
        )
        if products:
            return products[0]

        product_id = self._execute("product.product", "create", [{
            "name": name,
            "type": "product",  # Storable product
        }])
        log.info(f"  📦 Created product: {name} (id={product_id})")
        return product_id

    # ─── Main Post Method ─────────────────────────────────────────

    def post(self, data: dict, image_path: str = None) -> dict:
        """
        Post extracted data to Odoo. Creates:
        1. Supplier (if new)
        2. Vendor Bill → Account Payable
        3. Inventory receipt (if items)
        4. Expense entry
        Returns dict of created record IDs.
        """
        results = {}

        # Find or create supplier
        supplier_name = data.get("supplier_name")
        if not supplier_name:
            supplier_name = "Unknown Supplier"
            log.warning("  ⚠️ No supplier name found, using 'Unknown Supplier'")

        partner_id = self.find_or_create_supplier(
            supplier_name, data.get("supplier_vat")
        )
        results["partner_id"] = partner_id

        # Create vendor bill (Account Payable)
        try:
            bill_id = self.create_vendor_bill(data, partner_id)
            results["vendor_bill_id"] = bill_id
        except Exception as e:
            log.error(f"  ❌ Failed to create vendor bill: {e}")
            results["vendor_bill_error"] = str(e)

        # Create inventory receipt
        try:
            picking_id = self.create_inventory_receipt(data, partner_id)
            if picking_id:
                results["inventory_receipt_id"] = picking_id
        except Exception as e:
            log.error(f"  ❌ Failed to create inventory receipt: {e}")
            results["inventory_error"] = str(e)

        # Create expense entry
        try:
            expense_id = self.create_expense(data, partner_id)
            if expense_id:
                results["expense_id"] = expense_id
        except Exception as e:
            log.error(f"  ❌ Failed to create expense: {e}")
            results["expense_error"] = str(e)

        return results


if __name__ == "__main__":
    # Test connection
    import json as j
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(level=logging.INFO)
    poster = OdooPoster()
    try:
        poster._connect()
        print("✅ Odoo connection successful")
    except Exception as e:
        print(f"❌ Odoo connection failed: {e}")
