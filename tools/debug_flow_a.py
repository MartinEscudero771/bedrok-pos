import io
import json
import requests
import mysql.connector

B = "http://127.0.0.1:5000"
REF = "BEDROK-94CB08D85E9A"

env = {}
for line in io.open(".env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k] = v

c0 = mysql.connector.connect(host="localhost", user="root", password="0000", database="tienda_bedrok")
cur0 = c0.cursor(dictionary=True)
cur0.execute("SELECT id_factura, total, estado, pay_status FROM facturas WHERE codigo_referencia=%s", (REF,))
print("antes:", cur0.fetchall())
c0.close()

s = requests.Session()
s.post(B + "/login", data={"usuario": "admin", "clave": "admin"}, timeout=15)
rw = s.post(B + "/webhooks/factus-pay?key=" + env["FACTUS_PAY_WEBHOOK_KEY"], json={
    "data": {"reference_code": REF, "amount": 18564.0, "status": "paid",
             "payer": {"name": "Sim", "document_type": "CC", "document_number": "1"}}}, timeout=30)
print("webhook:", rw.status_code, rw.json())

c1 = mysql.connector.connect(host="localhost", user="root", password="0000", database="tienda_bedrok")
cur1 = c1.cursor(dictionary=True)
cur1.execute("SELECT id_factura, estado, pay_status FROM facturas WHERE codigo_referencia=%s", (REF,))
print("despues webhook:", cur1.fetchall())
c1.close()

r = s.get(B + "/api/recaudo/" + REF, timeout=120)
j = r.json()
print("poll pay:", (j.get("pay") or {}).get("status"), "| factura:", j.get("factura"))

c2 = mysql.connector.connect(host="localhost", user="root", password="0000", database="tienda_bedrok")
cur2 = c2.cursor(dictionary=True)
cur2.execute("SELECT estado, numero_factura, cufe FROM facturas WHERE codigo_referencia=%s", (REF,))
print("despues poll:", cur2.fetchall())
c2.close()
