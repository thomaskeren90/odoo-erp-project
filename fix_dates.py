lines = open("post_to_odoo.py").readlines()
new_line = (
    "        ds = date_str.replace(chr(39), chr(34)+chr(34)).strip()\n"
    "        if len(ds) <= 5: ds = ds + chr(34)/2026chr(34)\n"
    "        elif len(ds) == 7 and ds[2] == chr(34)/chr(34) and int(ds[3:5]) <= 4: ds = ds + chr(34)/2026chr(34)\n"
    "        elif len(ds) == 7 and ds[2] == chr(34)/chr(34): ds = ds + chr(34)/2025chr(34)\n"
    "        d = datetime.strptime(ds, chr(34)%d/%m/%Ychr(34))\n"
)
lines[23] = new_line
open("post_to_odoo.py", "w").writelines(lines)
print("fixed")
