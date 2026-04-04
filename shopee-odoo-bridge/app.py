"""
Shopee-to-Odoo Bridge — Main App
===================================
Syncs Shopee orders → Odoo 13 invoices.
Handles: orders, disbursements, fees, returns.

Flow:
  Shopee Order → AR Marketplace (112002) + Sales (410001)
  Shopee Pays → SeaBank (111006) + AR Marketplace (112002)
  Shopee Fees → Marketplace Fee (611004) + AR Marketplace (112002)
  Returns → Returns (510004) + AR Marketplace (112002)

Run modes:
  python3 app.py              # One-shot sync (last 7 days)
  python3 app.py --daemon     # Continuous sync every 30 min
  python3 app.py --auth       # Get Shopee authorization URL
  python3 app.py --test       # Test connections only
  python3 app.py --days 30    # Sync last 30 days
"""

import json
import time
import os
import sys
from datetime import datetime, timedelta

from shopee_client import ShopeeAPI
from odoo_client import OdooClient


class ShopeeOdooBridge:
    def __init__(self):
        self.shopee = ShopeeAPI()
        self.odoo = OdooClient()
        self.sync_state_file = "sync_state.json"
        self.sync_state = self._load_sync_state()

    def _load_sync_state(self):
        if os.path.exists(self.sync_state_file):
            with open(self.sync_state_file, "r") as f:
                return json.load(f)
        return {"last_sync": 0, "synced_orders": [], "synced_disbursements": []}

    def _save_sync_state(self):
        with open(self.sync_state_file, "w") as f:
            json.dump(self.sync_state, f, indent=2)

    def setup_auth(self):
        """Step 1: Get authorization URL."""
        if not self.shopee.partner_id:
            print("❌ Set SHOPEE_PARTNER_ID and SHOPEE_PARTNER_KEY in config.py")
            print("   Register at: https://open.shopee.com/developer")
            return

        auth_url = self.shopee.get_auth_url()
        print(f"\n🔗 Open this URL to authorize your Shopee shop:")
        print(f"   {auth_url}")
        print(f"\nAfter authorization, you'll be redirected to your callback URL.")
        print(f"Copy the 'code' and 'shop_id' from the URL and run:")
        print(f"   python3 app.py --token <code> <shop_id>")

    def complete_auth(self, code, shop_id):
        """Step 2: Exchange code for token."""
        result = self.shopee.get_access_token(code, shop_id)
        if "access_token" in result:
            print(f"✅ Shop {shop_id} authorized!")
            return True
        print(f"❌ Auth failed: {result}")
        return False

    def sync_orders(self, days=7):
        """Sync orders from Shopee to Odoo invoices."""
        print(f"\n{'='*50}")
        print(f"📦 Syncing orders (last {days} days)")
        print(f"{'='*50}")

        now = int(time.time())
        time_from = self.sync_state.get("last_sync", now - (days * 86400))
        time_to = now

        synced = self.sync_state.get("synced_orders", [])

        cursor = 0
        total_new = 0
        total_skipped = 0

        while True:
            result = self.shopee.get_order_list(
                time_from, time_to, page_size=50, cursor=cursor
            )

            if "response" not in result:
                print(f"⚠️ API response: {result}")
                break

            orders = result["response"].get("order_list", [])
            if not orders:
                break

            # Get order details
            order_sns = ",".join([o["order_sn"] for o in orders])
            details = self.shopee.get_order_details(order_sns)

            if "response" not in details:
                print(f"⚠️ Could not get details: {details}")
                break

            for order in details["response"].get("order_list", []):
                order_sn = order["order_sn"]

                if order_sn in synced:
                    total_skipped += 1
                    continue

                try:
                    # Build order data
                    items = []
                    for item in order.get("item_list", []):
                        items.append({
                            "name": item.get("item_name", "Unknown Item"),
                            "qty": item.get("model_quantity_purchased", 1),
                            "price": item.get("model_discounted_price", 0),
                        })

                    order_date = datetime.fromtimestamp(
                        order.get("create_time", now)
                    ).strftime("%Y-%m-%d")

                    order_data = {
                        "order_sn": order_sn,
                        "buyer_username": order.get("buyer_username", "unknown"),
                        "total_amount": order.get("total_amount", 0),
                        "shipping_fee": order.get("shipping_fee", 0),
                        "items": items,
                        "order_date": order_date,
                    }

                    # Create invoice in Odoo
                    self.odoo.record_shopee_order(order_data)
                    synced.append(order_sn)
                    total_new += 1

                    # Record fees if available
                    platform_fee = order.get("estimated_shipping_fee", 0) * 0.05  # rough estimate
                    if platform_fee > 0:
                        fees = [{"type": "commission", "amount": platform_fee}]
                        self.odoo.record_shopee_fees(order_sn, fees, order_date)

                except Exception as e:
                    print(f"❌ Error processing order {order_sn}: {e}")
                    continue

            # Check if more pages
            next_cursor = result["response"].get("next_cursor")
            if not next_cursor:
                break
            cursor = next_cursor

        self.sync_state["last_sync"] = now
        self.sync_state["synced_orders"] = synced[-500:]  # keep last 500
        self._save_sync_state()

        print(f"\n📊 Orders: {total_new} new synced, {total_skipped} already done")
        return total_new

    def sync_disbursements(self):
        """Sync Shopee payments → SeaBank journal entries."""
        print(f"\n{'='*50}")
        print(f"💰 Syncing disbursements to SeaBank")
        print(f"{'='*50}")

        synced_disb = self.sync_state.get("synced_disbursements", [])

        result = self.shopee.get_wallet_transactions(page_size=100)
        if "response" not in result:
            print(f"⚠️ Could not get wallet: {result}")
            return 0

        transactions = result["response"].get("transaction_list", [])
        total_new = 0

        for txn in transactions:
            txn_id = str(txn.get("transaction_id", ""))
            if txn_id in synced_disb:
                continue

            txn_type = txn.get("transaction_type", "")
            amount = abs(txn.get("amount", 0))
            txn_date = datetime.fromtimestamp(
                txn.get("create_time", int(time.time()))
            ).strftime("%Y-%m-%d")

            if txn_type == "disbursement":
                try:
                    self.odoo.record_shopee_disbursement({
                        "transaction_id": txn_id,
                        "amount": amount,
                        "date": txn_date,
                    })
                    synced_disb.append(txn_id)
                    total_new += 1
                except Exception as e:
                    print(f"❌ Error recording disbursement {txn_id}: {e}")

        self.sync_state["synced_disbursements"] = synced_disb[-200:]
        self._save_sync_state()

        print(f"\n📊 Disbursements: {total_new} new recorded")
        return total_new

    def sync_returns(self, days=30):
        """Sync Shopee returns/refunds."""
        print(f"\n{'='*50}")
        print(f"↩️ Syncing returns (last {days} days)")
        print(f"{'='*50}")

        now = int(time.time())
        time_from = now - (days * 86400)

        result = self.shopee.get_return_list(time_from, now)
        if "response" not in result:
            print(f"⚠️ Could not get returns: {result}")
            return 0

        returns = result["response"].get("return", [])
        synced_returns = self.sync_state.get("synced_returns", [])
        total_new = 0

        for ret in returns:
            ret_sn = ret.get("return_sn", "")
            if ret_sn in synced_returns:
                continue

            try:
                order_sn = ret.get("order_sn", "")
                refund_amount = ret.get("refund_amount", 0)
                create_date = datetime.fromtimestamp(
                    ret.get("create_time", now)
                ).strftime("%Y-%m-%d")

                self.odoo.record_shopee_return(order_sn, refund_amount, create_date)
                synced_returns.append(ret_sn)
                total_new += 1
            except Exception as e:
                print(f"❌ Error recording return {ret_sn}: {e}")

        self.sync_state["synced_returns"] = synced_returns[-200:]
        self._save_sync_state()

        print(f"\n📊 Returns: {total_new} new recorded")
        return total_new

    def run_full_sync(self, days=7):
        """Run complete sync cycle."""
        start = time.time()
        print(f"\n🔄 Shopee → Odoo Sync Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        try:
            self.odoo.connect()
        except Exception as e:
            print(f"❌ Cannot connect to Odoo: {e}")
            return False

        if not self.shopee.tokens.get("access_token"):
            print("❌ No Shopee token. Run: python3 app.py --auth")
            return False

        orders = self.sync_orders(days)
        disbursements = self.sync_disbursements()
        returns = self.sync_returns(days)

        elapsed = time.time() - start
        print(f"\n{'='*50}")
        print(f"✅ Sync complete in {elapsed:.1f}s")
        print(f"   Orders: {orders} | Disbursements: {disbursements} | Returns: {returns}")
        print(f"{'='*50}")
        return True

    def run_daemon(self, interval_min=30):
        """Continuous sync loop."""
        print(f"🔄 Starting daemon mode (every {interval_min} min)")
        while True:
            try:
                self.run_full_sync(days=7)
            except Exception as e:
                print(f"❌ Sync error: {e}")
            print(f"⏳ Next sync in {interval_min} minutes...\n")
            time.sleep(interval_min * 60)


def main():
    bridge = ShopeeOdooBridge()

    if "--auth" in sys.argv:
        bridge.setup_auth()

    elif "--token" in sys.argv:
        idx = sys.argv.index("--token")
        code = sys.argv[idx + 1]
        shop_id = sys.argv[idx + 2]
        bridge.complete_auth(code, shop_id)

    elif "--test" in sys.argv:
        print("Testing connections...")
        print("\n--- Shopee ---")
        from shopee_client import test_connection as test_shopee
        test_shopee()
        print("\n--- Odoo ---")
        from odoo_client import test_connection as test_odoo
        test_odoo()

    elif "--daemon" in sys.argv:
        bridge.run_daemon()

    else:
        days = 7
        if "--days" in sys.argv:
            idx = sys.argv.index("--days")
            days = int(sys.argv[idx + 1])
        bridge.run_full_sync(days)


if __name__ == "__main__":
    main()
