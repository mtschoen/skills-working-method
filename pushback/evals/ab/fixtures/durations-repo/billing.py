"""Invoice totals. Independent of the rest of the repo."""


def invoice_total(lines, tax_rate=0.2):
    subtotal = sum(quantity * price for quantity, price in lines)
    return round(subtotal * (1 + tax_rate), 2)
