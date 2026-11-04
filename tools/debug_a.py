import mysql.connector
import json

c = mysql.connector.connect(host="localhost", user="root", password="0000", database="tienda_bedrok")
cur = c.cursor(dictionary=True)
cur.execute("SELECT reference_code, status, id_factura FROM recaudos_pay ORDER BY id_recaudo DESC LIMIT 3")
print(cur.fetchall())
cur.execute("""
    SELECT codigo_http, estado_api, LEFT(mensaje, 200) AS mensaje
    FROM respuestas_factus WHERE id_factura=29 ORDER BY id_respuesta DESC LIMIT 4
""")
rt = cur.fetchall()
print(ct if (ct := None) else "")
for r in rt:
    print(r)
cur.execute("SELECT estado, cufe FROM facturas WHERE id_factura IN (29, 30, 23)")
print(cur.fetchall())
c.close()
