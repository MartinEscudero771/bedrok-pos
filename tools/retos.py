"""Verifica los flujos minimos requeridos del Reto Factus."""
import io
import json
import requests

B = "http://127.0.0.1:5000"
s = requests.Session()
s.post(B + "/login", data={"usuario": "admin", "clave": "admin"}, timeout=15)

print("=== 1. FLUJO B (facturacion previa): Factura DIAN primero + recaudo Bre-B ===")
r = s.post(B + "/guardar-factura", data={
    "cliente": "1",
    "productos_json": json.dumps([{"id": "2", "cantidad": 4}]),
    "metodo_pago": "BREB",
    "expiration": "900",
}, timeout=120)
j = r.json()
print("http:", r.status_code, "| factus:", j.get("factus_status"),
      "| pay:", (j.get("pay") or {}).get("status"), "| ref:", j.get("referencia"))
assert r.status_code == 200 and j.get("factus_status") == 201, "flujo B fallo"

print()
print("=== 2. FLUJO A (cobro previo): recaudo Bre-B primero (sin factura) ===")
r = s.post(B + "/crear-cobro-previo", data={
    "cliente": "1",
    "productos_json": json.dumps([{"id": "2", "cantidad": 2}]),
    "expiration": "900",
}, timeout=120)
j = r.json()
refA = j.get("referencia")
totalA = j.get("total")
qr_len = len((j.get("pay") or {}).get("qr") or "")
print("http:", r.status_code, "| pay:", (j.get("pay") or {}).get("status"),
      "| total:", totalA, "| qr_len:", qr_len, "| ref:", refA)
assert r.status_code == 200 and qr_len > 1000, "flujo A fallo creando recaudo"

print()
print("=== 3. Confirmar pago (simulador/webhook) y emision automatica de la factura ===")
env = dict()
for line in io.open(".env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k] = v
r = s.post(B + "/webhooks/factus-pay?key=" + env.get("FACTUS_PAY_WEBHOOK_KEY", ""), json={
    "data": {
        "reference_code": refA, "amount": totalA, "status": "paid",
        "created_at": "2026-11-04T12:00:00.000000Z", "qr_expires_at": None,
        "payer": {"name": "Simulador Bre-B", "document_type": "CC", "document_number": "555555"},
        "qr": None,
    }
}, timeout=30)
print("webhook:", r.status_code, r.json())

r2 = s.get(B + "/api/recaudo/" + refA, timeout=120)
j2 = r2.json()
print("poll pay:", (j2.get("pay") or {}).get("status"), "| factura:", j2.get("factura"))

import mysql.connector
c = mysql.connector.connect(host="localhost", user="root", password="0000", database="tienda_bedrok")
cur = c.cursor(dictionary=True)
cur.execute("SELECT estado, numero_factura, cufe, url_pdf FROM facturas WHERE codigo_referencia=%s", (refA,))
f = cur.fetchone()
print("en BD -> estado:", f["estado"], "| DIAN:", f["numero_factura"],
      "| cufe:", (f["cufe"] or "")[:20] if f["cufe"] else None, "| pdf:", bool(f["url_pdf"]))
c.close()

print()
print("=== 4. NOTA CREDITO sobre la factura del flujo A ===")
# obtener id de la factura emitida
cc = mysql.connector.connect(host="localhost", user="root", password="0000", database="tienda_bedrok")
c2 = cc.cursor(dictionary=True)
c2.execute("SELECT id_factura FROM facturas WHERE codigo_referencia=%s", (refA,))
idf = c2.fetchone()["id_factura"]
cc.close()
r3 = s.post(B + "/facturas/%d/nota-credito" % idf, timeout=120, allow_redirects=True)
print("nota credito http:", r3.status_code)
print("resultado:", "Nota credito generada correctamente" in r3.text or "rechazo la nota credito" in r3.text)

print()
print("=== 5. CONCILIACION en tiempo real ===")
r4 = s.get(B + "/api/conciliacion", timeout=30)
print(json.dumps(r4.json()["stats"], indent=1))

print()
print("=== 6. CONCILIAR manual (pull de Factus Pay) ===")
r5 = s.post(B + "/api/conciliar", timeout=120)
j5 = r5.json()
print("pagados:", j5.get("pagados"), "| emitidas:", j5.get("emitidas"), "| stats ok:", bool(j5.get("stats")))
