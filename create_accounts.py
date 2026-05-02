import xmlrpc.client
url = "http://localhost:8069"
db = "tokoodoo13"
user = "tokomakmur"
password = "admin123"
common = xmlrpc.client.ServerProxy(url + "/xmlrpc/2/common")
uid = common.authenticate(db, user, password, {})
models = xmlrpc.client.ServerProxy(url + "/xmlrpc/2/object")
accounts = [
    ("4100","Penjualan Spare Part",13),
    ("4110","Shopee Settlement",13),
    ("4200","Pendapatan Sewa Sigra",13),
    ("4300","Pendapatan Kos",13),
    ("4310","Pendapatan Listrik Kos",13),
    ("4400","Pendapatan Bunga",14),
    ("5100","Pembelian Irnawati",17),
    ("5110","Pembelian Aurora",17),
    ("5120","Pembelian Mastar",17),
    ("5130","Pembelian Zino",17),
    ("5140","Pembelian Feiyue",17),
    ("5150","Pembelian Lainnya",17),
    ("6100","Gaji Karyawan",15),
    ("6110","Biaya Packing Ekspedisi",15),
    ("6120","Biaya Platform Shopee",15),
    ("6200","Listrik Toko",15),
    ("6210","Listrik Kos",15),
    ("6220","Internet Telkom",15),
    ("6230","BPJS Kesehatan",15),
    ("6240","Biaya Administrasi Bank",15),
    ("6250","Biaya Kendaraan",15),
    ("6260","Top Up E-Wallet",15),
    ("6290","Biaya Kartu Kredit BCA",15),
    ("6300","Prive Thomas",15),
    ("1110","Uang Muka Supplier Irnawati",5),
    ("1120","Piutang Karyawan",5),
    ("2100","Shopee SpinJam Loan",9),
    ("2200","Hutang Keluarga Ibu",9),
]
created = 0
skipped = 0
for code, name, type_id in accounts:
    existing = models.execute_kw(db, uid, password, "account.account", "search", [[["code","=",code]]])
    if existing:
        print(f"EXISTS : {code} {name}")
        skipped += 1
        continue
    acc_id = models.execute_kw(db, uid, password, "account.account", "create", [{"code":code,"name":name,"user_type_id":type_id}])
    print(f"CREATED: {code} {name} (ID:{acc_id})")
    created += 1
print(f"Done! Created: {created}, Skipped: {skipped}")
