"""
Shopee Open Platform API Client
================================
Handles authentication, token refresh, and API calls to Shopee.
Uses API v2 with HMAC-SHA256 signing.

Docs: https://open.shopee.com/developer-guide/20
"""

import hashlib
import hmac
import json
import time
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

try:
    from config import (
        SHOPEE_PARTNER_ID, SHOPEE_PARTNER_KEY, SHOPEE_SHOP_ID,
        SHOPEE_BASE_URL, SHOPEE_REGION, SHOPEE_TOKEN_FILE
    )
except ImportError:
    SHOPEE_PARTNER_ID = os.environ.get("SHOPEE_PARTNER_ID", "")
    SHOPEE_PARTNER_KEY = os.environ.get("SHOPEE_PARTNER_KEY", "")
    SHOPEE_SHOP_ID = os.environ.get("SHOPEE_SHOP_ID", "")
    SHOPEE_BASE_URL = "https://partner.shopeemobile.com"
    SHOPEE_REGION = "ID"
    SHOPEE_TOKEN_FILE = "shopee_tokens.json"


class ShopeeAPI:
    def __init__(self):
        self.partner_id = SHOPEE_PARTNER_ID
        self.partner_key = SHOPEE_PARTNER_KEY
        self.shop_id = SHOPEE_SHOP_ID
        self.base_url = SHOPEE_BASE_URL
        self.tokens = self._load_tokens()

    def _load_tokens(self):
        if os.path.exists(SHOPEE_TOKEN_FILE):
            with open(SHOPEE_TOKEN_FILE, "r") as f:
                return json.load(f)
        return {}

    def _save_tokens(self):
        with open(SHOPEE_TOKEN_FILE, "w") as f:
            json.dump(self.tokens, f, indent=2)

    def _generate_sign(self, path, timestamp, access_token="", shop_id=""):
        """Generate HMAC-SHA256 signature per Shopee API v2 spec."""
        base_string = f"{self.partner_id}{path}{timestamp}"
        if access_token:
            base_string += access_token
        if shop_id:
            base_string += str(shop_id)
        return hmac.new(
            self.partner_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _api_call(self, method, path, params=None, body=None, auth=True):
        """Make authenticated API call to Shopee."""
        timestamp = int(time.time())
        access_token = self.tokens.get("access_token", "") if auth else ""

        sign = self._generate_sign(path, timestamp, access_token, self.shop_id)

        url = f"{self.base_url}{path}"
        url += f"?partner_id={self.partner_id}&timestamp={timestamp}&sign={sign}"
        if auth and self.shop_id:
            url += f"&shop_id={self.shop_id}"
        if auth and access_token:
            url += f"&access_token={access_token}"

        if params:
            for k, v in params.items():
                url += f"&{k}={v}"

        headers = {"Content-Type": "application/json"}
        data = json.dumps(body).encode() if body else None

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                if result.get("error"):
                    print(f"Shopee API error: {result['error']} - {result.get('message', '')}")
                return result
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            print(f"HTTP {e.code}: {error_body}")
            return {"error": e.reason, "message": error_body}

    # ==========================================
    # AUTH
    # ==========================================
    def get_auth_url(self, redirect_url="http://localhost:5000/callback"):
        """Generate authorization URL for shop owner to authorize the app."""
        timestamp = int(time.time())
        path = "/api/v2/shop/auth_partner"
        sign = self._generate_sign(path, timestamp)
        return (
            f"{self.base_url}{path}"
            f"?partner_id={self.partner_id}"
            f"&timestamp={timestamp}"
            f"&sign={sign}"
            f"&redirect={redirect_url}"
        )

    def get_access_token(self, code, shop_id):
        """Exchange auth code for access token."""
        timestamp = int(time.time())
        path = "/api/v2/auth/token/get"
        body = {"code": code, "shop_id": int(shop_id)}
        result = self._api_call("POST", path, body=body, auth=False)
        if "access_token" in result:
            self.tokens = {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "expire_at": result.get("expire_by", 0),
                "shop_id": int(shop_id),
            }
            self.shop_id = int(shop_id)
            self._save_tokens()
            print(f"✅ Token saved for shop {shop_id}")
        return result

    def refresh_access_token(self):
        """Refresh expired access token."""
        if not self.tokens.get("refresh_token"):
            print("No refresh token. Need to re-authorize.")
            return None
        timestamp = int(time.time())
        path = "/api/v2/auth/access_token/get"
        body = {
            "refresh_token": self.tokens["refresh_token"],
            "shop_id": int(self.shop_id),
        }
        result = self._api_call("POST", path, body=body, auth=False)
        if "access_token" in result:
            self.tokens = {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "expire_at": result.get("expire_by", 0),
            }
            self._save_tokens()
            print("✅ Token refreshed")
        return result

    def _ensure_valid_token(self):
        """Auto-refresh token if expired."""
        expire_at = self.tokens.get("expire_at", 0)
        if time.time() > expire_at - 300:  # refresh 5 min before expiry
            print("Token expiring soon, refreshing...")
            self.refresh_access_token()

    # ==========================================
    # ORDERS
    # ==========================================
    def get_order_list(self, time_from, time_to, page_size=100, cursor=0, status=None):
        """Get list of orders within time range.
        
        time_from/time_to: unix timestamp
        status: optional filter (UNPAID, READY_TO_SHIP, PROCESSED, etc.)
        """
        self._ensure_valid_token()
        params = {
            "time_from": time_from,
            "time_to": time_to,
            "page_size": page_size,
            "cursor": cursor,
            "order_statuses": status or "",
        }
        return self._api_call("GET", "/api/v2/order/get_order_list", params=params)

    def get_order_details(self, order_sn_list):
        """Get full details for specific orders.
        
        order_sn_list: comma-separated order numbers
        """
        self._ensure_valid_token()
        params = {"order_sn_list": order_sn_list}
        return self._api_call("GET", "/api/v2/order/get_order_detail", params=params)

    def get_shipping_parameter(self, order_sn):
        """Get shipping info for an order."""
        self._ensure_valid_token()
        params = {"order_sn": order_sn}
        return self._api_call("GET", "/api/v2/logistics/get_shipping_parameter", params=params)

    # ==========================================
    # PAYMENTS & FINANCE
    # ==========================================
    def get_wallet_transactions(self, page_size=100):
        """Get wallet transaction list (payments received)."""
        self._ensure_valid_token()
        params = {"page_size": page_size}
        return self._api_call("GET", "/api/v2/payment/get_wallet_transaction_list", params=params)

    # ==========================================
    # PRODUCTS
    # ==========================================
    def get_product_list(self, offset=0, page_size=100):
        """Get list of products in the shop."""
        self._ensure_valid_token()
        params = {"offset": offset, "page_size": page_size, "item_status": "NORMAL"}
        return self._api_call("GET", "/api/v2/product/get_item_list", params=params)

    def get_product_detail(self, item_id_list):
        """Get product details."""
        self._ensure_valid_token()
        params = {"item_id_list": item_id_list}
        return self._api_call("GET", "/api/v2/product/get_item_detail", params=params)

    # ==========================================
    # RETURNS
    # ==========================================
    def get_return_list(self, create_time_from, create_time_to, page_size=50):
        """Get return/refund requests."""
        self._ensure_valid_token()
        params = {
            "create_time_from": create_time_from,
            "create_time_to": create_time_to,
            "page_size": page_size,
        }
        return self._api_call("GET", "/api/v2/returns/get_return_list", params=params)


def test_connection():
    """Quick test of Shopee API connection."""
    api = ShopeeAPI()
    if not api.partner_id:
        print("❌ Missing SHOPEE_PARTNER_ID in config.py")
        print("   Register at https://open.shopee.com/developer")
        return False

    if not api.tokens.get("access_token"):
        auth_url = api.get_auth_url()
        print(f"🔗 Authorize your shop first:")
        print(f"   {auth_url}")
        print(f"   After authorization, you'll get a code. Use api.get_access_token(code, shop_id)")
        return False

    # Try getting order list (last 7 days)
    now = int(time.time())
    week_ago = now - (7 * 86400)
    result = api.get_order_list(week_ago, now, page_size=5)
    if "response" in result:
        count = len(result["response"].get("order_list", []))
        print(f"✅ Connected! Found {count} orders in last 7 days")
        return True
    else:
        print(f"⚠️ Connected but got: {result}")
        return True


if __name__ == "__main__":
    test_connection()
