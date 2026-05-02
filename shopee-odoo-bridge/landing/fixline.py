with open('invoice_bot.py', 'r') as f:
    lines = f.readlines()

with open('invoice_bot.py', 'w') as f:
    for i, line in enumerate(lines):
        if i == 24:
            f.write('    result = "Invoice Preview\\n\\n"\n')
            f.write('    result += "Supplier: " + str(data.get("supplier")) + "\\n"\n')
            f.write('    result += "Invoice No: " + str(data.get("invoice_number")) + "\\n"\n')
            f.write('    result += "Date: " + str(data.get("date")) + "\\n\\n"\n')
            f.write('    result += "Items:\\n"\n')
            f.write('    for l in data.get("lines", []):\n')
            f.write('        result += "  - " + str(l["description"]) + " x" + str(l["qty"]) + " = IDR " + str(l["total"]) + "\\n"\n')
            f.write('    result += "\\nTax: " + str(data.get("tax") or 0) + "\\n"\n')
            f.write('    result += "Total: IDR " + str(data.get("total")) + "\\n\\n"\n')
            f.write('    result += "Select posting type below:"\n')
            f.write('    return result\n')
        elif i == 25:
            pass
        else:
            f.write(line)
print('fixed')