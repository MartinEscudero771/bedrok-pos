"""Verifica detalladamente el outcome de la nota credito (exitoso o error de Factus)."""
import io
import json
import requests
import mysql.connector

B = "http://127.0.0.1:5000"
s = requests.Session()
s.post(B + "/login", data={"usuario": "admin", "clave": "admin"}, timeout=15)

c = mysql.connector.connect(host="localhost", user="root", password="0000", database="tienda_bedrok")
cur = c.cursor(dictionary=True)
cur.execute("""
    SELECT r.id_factura, r.codigo_http, r.estado_api, r.mensaje, r.respuesta_json
    FROM respuestas_factus r WHERE r.estado_api LIKE 'NC%'
    ORDER BY r.id_respuesta DESC LIMIT 1
""")
row = cur.fetchone()
if not row:
    raise SystemExit("sin notas credito registradas")
print("estado_api:", row["estado_api"], "| http:", row["codigo_http"])
print("mensaje:", row["mensaje"])
try:
    j = json.loads(row["respuesta_json"])
    print("respuesta Factus:", json.dumps(j, ensure_ascii=False)[:1200])
except Exception:
    print(row["respuesta_json"][:400])
c.close()
