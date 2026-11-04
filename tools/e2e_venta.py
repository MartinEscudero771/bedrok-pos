import json
import requests

s = requests.Session()
ok = s.post("http://127.0.0.1:5000/login", data={"usuario": "admin", "clave": "admin"}, timeout=15)
r = s.post(
    "http://127.0.0.1:5000/guardar-factura",
    data={
        "cliente": "1",
        "productos_json": json.dumps([{"id": "1", "cantidad": 2, "nombre": "t", "precio": 1, "iva": 19}]),
        "metodo_pago": "EFECTIVO",
    },
    timeout=90,
)
j = r.json()
print("HTTP:", r.status_code, "| success:", j.get("success"), "| ref:", j.get("referencia"), "| total:", j.get("total"))
print("factus:", j.get("factus_status"), "| pay:", (j.get("pay") or {}).get("status"))
print("ticket:", j.get("ticket_url"))
t = s.get("http://127.0.0.1:5000" + j.get("ticket_url"), timeout=15)
print("ticket HTTP:", t.status_code)
print("miles en ticket:", ("29.750" in t.text), "| sin watermark:", ("Sandbox - documento" not in t.text))
