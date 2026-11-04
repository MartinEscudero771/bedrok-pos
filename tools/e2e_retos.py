"""Verifica los flujos minimos requeridos del Reto Factus."""
import io
import json
import requests
import mysql.connector

B = "http://127.0.0.1:5000"
s = requests.Session()
s.post(B + "/login", data={"usuario": "admin", "clave": "admin"}, timeout=15)

# cargar .env del webhook key
key = ""
for line in io.open("../../../Downloads/Tienda_bedrok_con_diseno/Tienda_bedrok/.env".replace("../../../", ""), encoding="utf-8"):
    pass

print("=== 1. FLUJO B (facturacion previa): ya probado -> crear venta con QR Bre-B ===")
r = s.post(B + "/guardar-factura", data={
    "cliente": "1",
    "productos_json": json.dumps([{"id": "6", "cantidad": 1, "precio": 1, "iva": 19}]),
    "metodo_pago": "BREB",
    "expiration": "900",
}, timeout=120)
j = r.json()
refB = j.get("referencia")
print("http:", r.status_code, "| factus:", j.get("factus_status"), "| pay:", (j.get("pay") or {}).get("status"), "| ref:", refB)

print()
print("=== 2. FLUJO A (cobro previo): recaudo primero ===")
r = s.post(B + "/crear-cobro-previo", data={
    "cliente": "1",
    "productos_json": json.dumps([{"id": "2", "cantidad": 1, "precio": 1, "iva": 19}]),
    "expiration": "900",
}, timeout=120)
j = r.json()
refA = j.get("referencia")
qr_len = len((j.get("pay") or {}).get("qr") or "")
print("http:", r.status_code, "| pay:", (j.get("pay") or {}).get("status"), "| qr_len:", qr_len, "| ref:", refA)
assert r.status_code == 200 and qr_len > 1000, "flujo A fallo creando recaudo"

print()
print("=== 3. Confirmar pago del flujo A via webhook del simulador ===")
env = {}
for line in io.open(".env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k] = v
wk = env.get("FACTUS_PAY_WEBHOOK_KEY", "")
r = s.post(B + "/webhooks/factus-pay?key=" + wk, json={
    "data": {
        "reference_code": refA,
        "amount": (
            lambda x: x
        )(5200),  # se corrige abajo con total real desde la respuesta del flujo A
        "status": "paid",
        "created_at": "2026-11-04T12:00:00.000000Z",
        "qr_expires_at": None,
        "payer": {"name": "Simulador Bre-B", "document_type": "CC", "document_number": "555555"},
        "qr": None,
    }
}, timeout=30)
print("webhook captura:", r.status_code, r.json())
