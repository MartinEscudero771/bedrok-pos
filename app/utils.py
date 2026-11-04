# --------------------------------------------------
# Utilidades: formato de moneda COP (separador de miles con punto)
# 555555 -> 555.555
# --------------------------------------------------
from decimal import Decimal, ROUND_HALF_UP


def fmt_cop(value):
    """Formatea un numero al estilo colombiano: 12500 -> 12.500 ; 14875.5 -> 14.875,50"""
    try:
        d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return str(value)
    neg = d < 0
    d = abs(d)
    entero = int(d)
    centavos = int((d - entero) * 100)
    texto = f"{entero:,}".replace(",", ".")
    if centavos:
        texto += f",{centavos:02d}"
    return ("-" if neg else "") + texto


def fmt_num(value):
    """Solo separador de miles sobre la parte entera."""
    try:
        d = Decimal(str(value))
    except Exception:
        return str(value)
    entero = int(d.to_integral_value(rounding=ROUND_HALF_UP))
    return f"{entero:,}".replace(",", ".")


def fmt_moneda(value):
    """Formato internacional en pesos (USD): 1234.5 -> 1,234.50"""
    try:
        d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return str(value)
    return f"{d:,.2f}"
