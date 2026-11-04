"""Checklist final del Reto Factus + requisitos de la interfaz."""
import io
import json
import requests

B = "http://127.0.0.1:5000"
s = requests.Session()
s.post(B + "/login", data={"usuario": "admin", "clave": "admin"}, timeout=15)

ok = lambda t, c: print(("PASS " if c else "FAIL ") + t)

# 1. Navegacion y assets
for u, name in [("/pos", "pos"), ("/pedidos", "internacionales"), ("/clientes", "clientes"),
                ("/productos", "productos"), ("/crear-factura", "facturar"),
                ("/facturas", "historial"), ("/static/img/favicon.ico", "favicon"),
                ("/static/img/logo.svg", "logo")]:
    st = s.get(B + u, timeout=25).status_code
    ok(name + "->200", st == 200)

pos = s.get(B + "/pos", timeout=25).text
ok("POS renombrado 'POS Web con Facturacion Electronica'", "POS Web con Facturacion Electronica" in pos)
ok("Opciones A y B visibles en POS", "Opcion A - Cobro previo" in pos and "Opcion B - Facturacion previa" in pos)
ok("Modal con Descargar QR / Imprimir QR", "btnQrDl" in pos and "imprimirQR" in pos)
ok("Favicon referenciado en POS", "favicon.ico" in pos)

ped = s.get(B + "/pedidos", timeout=25).text
ok("Pedidos: tasa en vivo (tasaAct + refresco automatico)", "tasaAct" in ped and "60000" in io.open("static/js/pedidos.js", encoding="utf-8").read())

hist = s.get(B + "/facturas", timeout=25).text
ok("Historial: panel conciliacion tiempo real", "statsConci" in hist and "Conciliar con Factus Pay" in hist)
ok("Historial: boton Nota credito en validadas", "nota-credito" in hist)

ui = io.open("static/js/ui.js", encoding="utf-8").read()
ok("Barra de progreso + texto de segundos esperando", "showProgress" in ui and "progress-bar" in ui and "s restantes" in ui)

# 2. Flujo A completo end-to-end (recaudo -> pago simulado -> factura emitida)
print()
print("-- FLUJO A (cobro previo) --")
r = s.post(B + "/guardar-factura", data={
    "cliente": "1",
    "productos_json": json.dumps([{"id": "2", "cantidad": 3}]),
    "metodo_pago": "PREVIO",
    "expiration": "900",
}, timeout=120)
j = r.json()
refA, totalA = j.get("referencia"), j.get("total")
ok("Recaudo Bre-B creado (sin factura): " + refA, r.status_code == 200 and len(((j.get("pay") or {}).get("qr")) or "") > 1000)
env = {}
for line in io.open(".env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k] = v
rw = s.post(B + "/webhooks/factus-pay?key=" + env.get("FACTUS_PAY_WEBHOOK_KEY", ""), json={
    "data": {"reference_code": refA, "amount": totalA, "status": "paid",
             "payer": {"name": "Simulador", "document_type": "CC", "document_number": "1"}}}, timeout=30)
ok("Pago confirmado por webhook (Factus Pay)", rw.status_code == 200)
rp = s.get(B + "/api/recaudo/" + refA, timeout=120).json()
fi = rp.get("factura") or {}
ok("Factura DIAN emitida automaticamente: " + str(fi.get("numero_factura")), (rp.get("pay") or {}).get("status") == "paid" and fi.get("emitida"))

# 3. Nota credito de anulación
print()
print("-- NOTA CREDITO --")
import mysql.connector
c = mysql.connector.connect(host="localhost", user="root", password="0000", database="tienda_bedrok")
cur = c.cursor()
cur.execute("SELECT id_factura FROM facturas WHERE codigo_referencia=%s", (refA,))
idf = cur.fetchone()[0]
c.close()
rh = s.post(B + "/facturas/%d/nota-credito" % idf, timeout=120, allow_redirects=True)
ok("Nota credito creada y validada por la DIAN", "Nota credito generada correctamente" in rh.text)

# 4. Conciliacion
print()
print("-- CONCILIACION --")
st = s.get(B + "/api/conciliacion", timeout=30).json()["stats"]
ok("Stats operacionales en tiempo real", st["ventas_hoy"] > 0 and st["validadas_hoy"] > 0)
print(json.dumps(st, indent=1))
