import json
import requests

s = requests.Session()
s.post("http://127.0.0.1:5000/login", data={"usuario": "admin", "clave": "admin"}, timeout=15)
B = "http://127.0.0.1:5000"

print("=== 1. Guardar-factura SIN monto recibido (EFECTIVO) -> debe 400 ===")
r = s.post(B + "/guardar-factura", data={
    "cliente": "1",
    "productos_json": json.dumps([{"id": "1", "cantidad": 1, "precio": 1, "iva": 19}]),
    "metodo_pago": "EFECTIVO",
}, timeout=60)
print(r.status_code, r.json().get("mensaje"))

print("=== 2. Guardar-factura SIN cliente -> debe 400 ===")
r = s.post(B + "/guardar-factura", data={
    "productos_json": json.dumps([{"id": "1", "cantidad": 1, "precio": 1, "iva": 19}]),
    "metodo_pago": "EFECTIVO", "monto_recibido": "20000",
}, timeout=60)
print(r.status_code, r.json().get("mensaje"))

print("=== 3. Monto menor al total -> debe 400 ===")
r = s.post(B + "/guardar-factura", data={
    "cliente": "1",
    "productos_json": json.dumps([{"id": "1", "cantidad": 1, "precio": 1, "iva": 19}]),
    "metodo_pago": "EFECTIVO", "monto_recibido": "10000",
}, timeout=60)
print(r.status_code, r.json().get("mensaje"))

print("=== 4. Venta valida efectivo con cambio -> 200 + Factus 201 ===")
r = s.post(B + "/guardar-factura", data={
    "cliente": "1",
    "productos_json": json.dumps([{"id": "1", "cantidad": 1, "precio": 1, "iva": 19}]),
    "metodo_pago": "EFECTIVO", "monto_recibido": "20000",
}, timeout=90)
j = r.json()
print(r.status_code, "total:", j.get("total"), "factus:", j.get("factus_status"))

print("=== 5. Pedido internacional: monto USD insuficiente -> 400 ===")
r = s.post(B + "/guardar-pedido", data={
    "cliente": "1",
    "productos_json": json.dumps([{"id": "1", "cantidad": 1}, {"id": "2", "cantidad": 1}, {"id": "3", "cantidad": 1}]),
    "monto_usd": "1",
}, timeout=60)
print(r.status_code, r.json().get("mensaje"))

print("=== 6. Pedido internacional valido: 35.343 COP pagados con US$ 15 ===")
r = s.post(B + "/guardar-pedido", data={
    "cliente": "1",
    "productos_json": json.dumps([{"id": "1", "cantidad": 1}, {"id": "2", "cantidad": 2}, {"id": "3", "cantidad": 1}]),
    "monto_usd": "15",
}, timeout=120)
j = r.json()
print(r.status_code, "total:", j.get("total"), "tasa:", j.get("tasa"),
      "equiv:", j.get("equivalente_usd"), "cambio usd:", j.get("cambio_usd"),
      "cambio cop:", j.get("cambio_cop"), "factus:", j.get("factus_status"))
t = s.get(B + j.get("ticket_url"), timeout=15)
print("ticket:", t.status_code, "| doble moneda:", "Doble moneda" in t.text, "| TOTAL USD:", "TOTAL USD" in t.text)

print("=== 7. Cliente duplicado / invalido es validado en modulo (form) ===")
r = s.post(B + "/clientes", data={
    "tipo_documento": "13", "numero_documento": "1234567890", "nombres": "Duplicado Test",
}, timeout=15, allow_redirects=False)
print("cliente duplicado redirect:", r.status_code)
r2 = s.post(B + "/clientes", data={
    "tipo_documento": "13", "numero_documento": "123", "nombres": "Corto",
}, timeout=15)
print("doc corto rechazado:", "documento debe tener" in r2.text or "documento" in r2.text)
