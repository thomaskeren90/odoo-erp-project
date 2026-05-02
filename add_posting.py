# placeholder
import os, re, json, csv
from datetime import datetime
from google import genai
import xmlrpc.client
import pdfplumber

GEMINI_API_KEY = "AIzaSyAbNFQqmn0UxHOgT7Tg-3lEhTXSr9rfB_Y"
ODOO_URL = "http://localhost:8069"
ODOO_DB = "tokoodoo13"
ODOO_USER = "tokomakmur"
ODOO_PASSWORD = "admin123"

MY_ACCOUNTS = ["472", "535", "5300138677", "THOMAS SUSIN CHEN", "SAQU", "SEABANK"]

RULES = {
    "ATRANS DIGITAL SIN": ("4200", "Pendapatan Sewa Sigra"),
    "SHOPEE SELLER WALLET": ("4110", "Shopee Settlement"),
    "SPINJAM PENJUAL": ("2100", "Shopee SpinJam Loan"),
    "bayar spinjam": ("2100", "Shopee SpinJam Loan"),
    "biaya spinjam": ("2100", "Shopee SpinJam Loan"),
    "TETI ALAWIYAH": ("4310", "Pendapatan Kos"),
    "uang kos": ("4310", "Pendapatan Kos"),
    "uang kost": ("4310", "Pendapatan Kos"),
    "FIRMAN": ("4310", "Pendapatan Kos"),
    "IRNAWATI": ("5100", "Pembelian Irnawati"),
    "CV AURORA SEJAHTER": ("5110", "Pembelian Aurora"),
    "MASTAR PERDANA": ("5120", "Pembelian Mastar"),
    "ZINO INDONESIA": ("5130", "Pembelian Zino"),
    "LIN LING YIN": ("5140", "Pembelian Feiyue"),
    "feiyue": ("5140", "Pembelian Feiyue"),
    "WARUNG BENANG": ("5150", "Pembelian Lainnya"),
    "CAI HUIZHONG": ("5150", "Pembelian Lainnya"),
    "JAYA JAMRUD": ("5150", "Pembelian Lainnya"),
    "ERA SINERGIS": ("5150", "Pembelian Lainnya"),
    "LIE WANDY": ("5150", "Pembelian Lainnya"),
    "bayar bon": ("5150", "Pembelian Lainnya"),
    "bayar aurora": ("5110", "Pembelian Aurora"),
    "bayar zino": ("5130", "Pembelian Zino"),
    "bayar feiyue": ("5140", "Pembelian Feiyue"),
    "biaya gaji": ("6100", "Gaji Karyawan"),
    "biaya kos": ("6100", "Biaya Kos Karyawan"),
    "PLN PREPAID": ("6200", "Listrik Toko"),
    "PLN JKT": ("6210", "Listrik Kos"),
    "PLN TGR": ("6210", "Listrik Kos"),
    "TELKOM": ("6220", "Internet Telkom"),
    "INDIHOME": ("6220", "Internet Telkom"),
    "Telkomsel": ("6220", "Internet Telkom"),
    "BPJS": ("6230", "BPJS Kesehatan"),
    "BIAYA ADM": ("6240", "Biaya Administrasi Bank"),
    "SPBU": ("6250", "Biaya Kendaraan"),
    "mobilio": ("6250", "Biaya Kendaraan"),
    "GOPAY TOPUP": ("6260", "Top Up E-Wallet"),
    "DANA": ("6260", "Top Up E-Wallet"),
    "OVO": ("6260", "Top Up E-Wallet"),
    "FLAZZ": ("6260", "Top Up E-Wallet"),
    "biaya prvt": ("6300", "Prive Thomas"),
    "TARIKAN ATM": ("6300", "Prive Thomas"),
    "KARTU KREDIT": ("6290", "Biaya Kartu Kredit BCA"),
    "BCA CARD": ("6290", "Biaya Kartu Kredit BCA"),
    "PAM": ("6210", "Air Kos"),
    "M DAEN ISKANDAR": ("6100", "Gaji Daen"),
    "biaya daen": ("6100", "Gaji Daen"),
    "bayar daen": ("6100", "Gaji Daen"),
    "inter brother": ("5150", "Pembelian Lainnya"),
    "SUSANNA": ("5150", "Pembelian Lainnya"),
    "setoran": ("4100", "Penjualan Tunai"),
    "SETORAN TUNAI": ("4100", "Penjualan Tunai"),
    "EFENDI": ("5150", "Pembelian CWS"),
    "biaya sigra": ("5150", "Pembelian CWS"),
    "biaya czw": ("5150", "Pembelian CWS"),
    "bayar czw": ("5150", "Pembelian CWS"),
    "bayar ban": ("5150", "Pembelian CWS"),
    "KELVIN WINATA": ("5150", "Pembelian CWS"),
    "NURHUDA": ("5150", "Pembelian CWS"),
    "LI ZHIQIANG": ("4100", "Penjualan Spare Part"),
    "DERMAN NAPITUPULU": ("4100", "Penjualan Spare Part"),
    "KEVIN WILIANDY": ("4100", "Penjualan Spare Part"),
    "LING YUN": ("4100", "Penjualan Spare Part"),
    "ANIEK MEGAWATI": ("4100", "Penjualan Mesin"),
    "setor penjualan": ("4100", "Penjualan Tunai"),
    "Dp mesin": ("4100", "Penjualan Mesin DP"),
    "Pelunasan": ("4100", "Penjualan Mesin Lunas"),
    "SHOPEE": ("6120", "Biaya Platform Shopee"),
    "QR  014": ("6260", "Pembayaran QR"),
    "TRANSAKSI DEBIT": ("6260", "Pembayaran QR"),
    "FARMERS": ("6260", "Pembayaran QR"),
    "mulia jaya": ("5150", "Pembelian Lainnya"),
    "TAN SUI": ("5150", "Pembelian Lainnya"),
    "perniagaan raya": ("6300", "Biaya Sewa"),
    "ANNA": ("6300", "Biaya Sewa"),
    "bayar colokan": ("6100", "Biaya Operasional"),
    "BAYUDIN": ("6100", "Biaya Operasional"),
    "AULIA FAJRIN": ("5150", "Pembelian Lainnya"),
    "biaya packing": ("6110", "Biaya Packing"),
    "bayar packing": ("6110", "Biaya Packing"),
    "bayar dinamo": ("5150", "Pembelian Spare Part"),
    "bayar servo": ("5150", "Pembelian Spare Part"),
    "bayar setvo": ("5150", "Pembelian Spare Part"),
    "bayar kambing": ("5150", "Pembelian Lainnya"),
    "bayar mulia": ("5150", "Pembelian Lainnya"),
    "bayar bayu": ("6100", "Gaji Karyawan"),
    "bayar darn": ("6100", "Gaji Karyawan"),
    "biaya um": ("6100", "Uang Muka Karyawan"),
    "GARIN": ("5150", "Pembelian Lainnya"),
    "WIWIN": ("6100", "Biaya Kos Karyawan"),
    "LIE WANDY": ("5150", "Pembelian Lainnya"),
    "bayar sisa": ("5150", "Pembelian Lainnya"),
    "bayar wandi": ("5150", "Pembelian Lainnya"),
    "FTQRS": ("5150", "Pembelian QR Payment"),
    "ARSIAH": ("5150", "Pembelian Meja Mesin"),
    "ADHY WILLY": ("6240", "Biaya Pajak/Akuntan"),
    "SUTRISNO": ("4100", "Penjualan Toko"),
    "GRANDLUCKY": ("6300", "Prive Belanja Pribadi"),
    "Freedom I": ("6220", "Internet HP Toko"),
    "FI 9GB": ("6220", "Internet HP Toko"),
    "FI 7GB": ("6220", "Internet HP Toko"),
    "FI 18GB": ("6220", "Internet HP Toko"),
    "FADLI": ("4100", "Penjualan Toko"),
    "DAVID TANSIL": ("4100", "Penjualan Toko"),
    "SWITCHING CR": ("4100", "Penjualan QR"),
    "MAKSUS": ("6100", "Gaji Karyawan"),
    "bayar maksus": ("6100", "Gaji Karyawan"),
    "bayar erni": ("5150", "Pembelian Lainnya"),
    "ERA SINERGIS": ("5150", "Pembelian Lainnya"),
    "CAI HUIZHONG": ("5150", "Pembelian Lainnya"),
    "biaya cai": ("5150", "Pembelian Lainnya"),
    "JAYA JAMRUD": ("5150", "Pembelian Spare Part"),
    "MUHAMMAD CHOIR": ("5150", "Pembelian Spare Part"),
    "biaya kost": ("6100", "Biaya Kos Karyawan"),
    "biaya lifung": ("5100", "Pembelian Irnawati"),
    "bayar irna": ("5100", "Pembelian Irnawati"),
    "biaya irnawati": ("5100", "Pembelian Irnawati"),
    "biaya siruba": ("5120", "Pembelian Mastar Siruba"),
    "KARTU DEBIT": ("6300", "Prive Kartu Debit"),
    "tk pinjam": ("1120", "Piutang Karyawan"),
    "uang kos bulan": ("4310", "Pendapatan Kos"),
    "DAVID WIJAYA": ("5150", "Pembelian Lainnya"),
    "bayar kompor": ("5150", "Pembelian Lainnya"),
    "DEDI ANWAR": ("5150", "Pembelian Lainnya"),
    "ANGGI FERDIAN": ("4200", "Pendapatan Sewa Mesin DHS"),
    "SUIKMAN": ("4100", "Penjualan Toko"),
    "IWANTO": ("5150", "Pembelian Spare Part"),
    "siksak": ("5150", "Pembelian Spare Part"),
    "PATINDA": ("5150", "Pembelian Lainnya"),
    "ARJUNA JAYA": ("5150", "Pembelian Lainnya"),
    "WU QIHUAI": ("5150", "Pembelian Lainnya"),
    "SANDRA SAERANG": ("6110", "Biaya Ekspedisi"),
    "biaya ekspedisi": ("6110", "Biaya Ekspedisi"),
    "ANTON MULIA": ("5150", "Pembelian Lainnya"),
    "biaya jangsin": ("5150", "Pembelian Lainnya"),
    "jangsin": ("5150", "Pembelian Lainnya"),
    "FLEMING": ("5150", "Pembelian Lainnya"),
    "SAKIMIN": ("5150", "Pembelian Lainnya"),
    "qmove": ("5150", "Pembelian Lainnya"),
    "bayar barcode": ("6240", "Biaya Software/Barcode"),
    "barcode+software": ("6240", "Biaya Software/Barcode"),
    "biaya toko": ("6100", "Biaya Operasional Toko"),
    "biaya karung": ("5150", "Pembelian Karung"),
    "EGI SAPRUDIN": ("5150", "Pembelian Lainnya"),
    "biaya baraka": ("5150", "Pembelian Lainnya"),
    "ARTA MUARA": ("6260", "Pembayaran QR"),
    "MCDONALD": ("6300", "Prive Makan"),
    "OVO": ("6260", "Top Up OVO"),
    "bayar baleno": ("5150", "Pembelian Lainnya"),
    "bayar qmove": ("5150", "Pembelian Lainnya"),
    "TJOI SIOE CHIN": ("6300", "Transfer Keluarga"),
    "2... CR": ("4100", "Penjualan Toko"),
    "DIAN LESTIANI": ("5150", "Pembelian CWS"),
}

def is_own_transfer(desc, amount):
    desc_upper = desc.upper()
    for acc in MY_ACCOUNTS:
        if acc.upper() in desc_upper:
            return True
    try:
        amt_int = int(float(amount))
        if str(amt_int).endswith("001"):
            return True
    except:
        pass
    return False

def classify_transaction(desc):
    desc_lower = desc.lower()
    for keyword, (account, name) in RULES.items():
        if keyword.lower() in desc_lower:
            return account, name
    return None, None

def parse_bca_csv(filepath):
    transactions = []
    with open(filepath, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    for line in lines[5:]:
        parts = line.strip().split(",")
        if len(parts) < 5:
            continue
        date_raw = parts[0].strip().replace("'", "")
        if date_raw in ["PEND", "Saldo", "Kredit", "Debet", ""]:
            continue
        try:
            desc = parts[1].strip()
            amount = float(parts[3].replace(",", "."))
            cr_db = parts[4].strip()
            transactions.append({
                "date": date_raw,
                "desc": desc,
                "amount": amount,
                "cr_db": cr_db,
                "source": "BCA"
            })
        except:
            continue
    return transactions

def parse_seabank_pdf(filepath):
    transactions = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split("\n")
            i = 0
            while i < len(lines):
                line = lines[i]
                if "Shopee Seller Wallet" in line:
                    for j in range(i, min(i+3, len(lines))):
                        nums = re.findall(r"[\d\.]+", lines[j].replace(",", "."))
                        for n in nums:
                            try:
                                amt = float(n.replace(".", ""))
                                if amt > 100000:
                                    transactions.append({"date": "SEA", "desc": "Shopee Seller Wallet", "amount": amt, "cr_db": "CR", "source": "Seabank"})
                                    break
                            except:
                                pass
                if "SPinjam Penjual" in line:
                    for j in range(i, min(i+3, len(lines))):
                        nums = re.findall(r"[\d\.]+", lines[j].replace(",", "."))
                        for n in nums:
                            try:
                                amt = float(n.replace(".", ""))
                                if amt > 100000:
                                    transactions.append({"date": "SEA", "desc": "SPinjam Penjual", "amount": amt, "cr_db": "DB", "source": "Seabank"})
                                    break
                            except:
                                pass
                i += 1
    return transactions

def odoo_connect():
    common = xmlrpc.client.ServerProxy(ODOO_URL + "/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(ODOO_URL + "/xmlrpc/2/object")
    return uid, models

def get_account_id(models, uid, code):
    ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
        "account.account", "search", [[["code", "=", code]]])
    return ids[0] if ids else None

def process(bca_file=None, seabank_file=None, dry_run=True):
    all_tx = []
    if bca_file:
        print(f"Reading BCA: {bca_file}")
        all_tx += parse_bca_csv(bca_file)
    if seabank_file:
        print(f"Reading Seabank: {seabank_file}")
        all_tx += parse_seabank_pdf(seabank_file)

    print(f"Total transactions found: {len(all_tx)}")

    uid, models = odoo_connect()
    posted = 0
    skipped = 0
    unclassified = []

    for tx in all_tx:
        if is_own_transfer(tx["desc"], tx["amount"]):
            skipped += 1
            continue
        account_code, account_name = classify_transaction(tx["desc"])
        if not account_code:
            unclassified.append(tx)
            continue
        prefix = "[DRY RUN] " if dry_run else ""
        print(f"{prefix}{tx['date']} | {tx['cr_db']} {tx['amount']:>12,.0f} | {account_code} {account_name} | {tx['desc'][:45]}")
        posted += 1

    print(f"\n{'='*60}")
    print(f"Classified : {posted}")
    print(f"Skipped    : {skipped} (own account transfers)")
    print(f"Unclassified: {len(unclassified)}")
    if unclassified:
        print(f"\n--- NEEDS YOUR REVIEW ---")
        for tx in unclassified:
            print(f"  {tx['date']} | {tx['cr_db']} {tx['amount']:>10,.0f} | {tx['desc'][:55]}")

if __name__ == "__main__":
    import sys
    bca = sys.argv[1] if len(sys.argv) > 1 else None
    sea = sys.argv[2] if len(sys.argv) > 2 else None
    process(bca_file=bca, seabank_file=sea, dry_run=False)