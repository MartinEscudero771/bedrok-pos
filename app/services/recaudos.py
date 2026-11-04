# --------------------------------------------------
# SERVICIOS: helpers de recaudos Bre-B sobre la BD local
# --------------------------------------------------
import json

from ..database import conectar


def guardar_recaudo_db(id_factura, reference_code, amount, pay_http, pay_json):
    """Guarda/actualiza el recaudo Bre-B en MySQL. Devuelve dict normalizado."""
    data = (pay_json or {}).get("data") or {}
    status = str(data.get("status") or ("ready" if pay_http in (200, 201) else "error")).lower()
    breb_key = data.get("breb_key")
    qr = data.get("qr")
    qr_expires = data.get("qr_expires_at")
    collected = data.get("collected_at")

    con = conectar()
    if not con:
        return {"status": status, "qr": qr, "breb_key": breb_key,
                "qr_expires_at": qr_expires, "collected_at": collected}
    cur = con.cursor(dictionary=True)
    try:
        cur.execute("SELECT id_recaudo, status FROM recaudos_pay WHERE reference_code=%s", (reference_code,))
        existe = cur.fetchone()
        # Idempotencia: si ya se confirmo pagado, no degradar con 'ready' del polling
        if existe and existe["status"] == "paid" and status != "paid":
            status = "paid"
        if existe:
            cur.execute("""
                UPDATE recaudos_pay SET id_factura=%s, amount=%s, status=%s, breb_key=%s,
                    qr=%s, qr_expires_at=%s, collected_at=%s, raw_json=%s
                WHERE reference_code=%s
            """, (id_factura, amount, status, breb_key, qr, str(qr_expires or ""),
                  str(collected or ""), json.dumps(pay_json)[:60000], reference_code))
        else:
            cur.execute("""
                INSERT INTO recaudos_pay
                (id_factura, reference_code, amount, status, breb_key, qr, qr_expires_at, collected_at, raw_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (id_factura, reference_code, amount, status, breb_key, qr,
                  str(qr_expires or ""), str(collected or ""), json.dumps(pay_json)[:60000]))
        pay_status = "PAGADO" if status == "paid" else ("LISTO_QR" if status == "ready" else "ERROR_PAY")
        cur.execute("""
            UPDATE facturas SET pay_reference=%s, pay_status=%s
            WHERE id_factura=%s AND (pay_status IS NULL OR pay_status NOT IN ('PAGADO'))
        """, (reference_code, pay_status, id_factura))
        con.commit()
    except Exception as e:
        print("guardar_recaudo_db:", e)
        try:
            con.rollback()
        except Exception:
            pass
    finally:
        try:
            cur.close()
            con.close()
        except Exception:
            pass
    return {"status": status, "qr": qr, "breb_key": breb_key,
            "qr_expires_at": qr_expires, "collected_at": collected}


def datos_ticket(id_factura):
    """Datos completos para el ticket termico: factura + detalle + recaudo."""
    con = conectar()
    if not con:
        return None
    cur = con.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT f.*, c.nombres AS cliente_nombre, c.numero_documento,
                   c.tipo_documento, c.telefono AS cli_tel, c.direccion AS cli_dir, c.correo AS cli_mail
            FROM facturas f JOIN clientes c ON c.id_cliente=f.id_cliente
            WHERE f.id_factura=%s
        """, (id_factura,))
        fac = cur.fetchone()
        if not fac:
            return None
        cur.execute("""
            SELECT d.*, p.nombre, p.codigo_referencia
            FROM detalle_factura d JOIN productos p ON p.id_producto=d.id_producto
            WHERE d.id_factura=%s ORDER BY d.id_detalle
        """, (id_factura,))
        detalle = cur.fetchall()
        ref = fac.get("pay_reference") or fac.get("codigo_referencia")
        cur.execute(
            "SELECT * FROM recaudos_pay WHERE reference_code=%s OR id_factura=%s"
            " ORDER BY id_recaudo DESC LIMIT 1",
            (ref, id_factura),
        )
        rec = cur.fetchone()
        if not rec:
            cur.execute("SELECT * FROM recaudos_pay WHERE reference_code=%s LIMIT 1",
                        (fac.get("codigo_referencia"),))
            rec = cur.fetchone()
        return {"factura": fac, "detalle": detalle, "recaudo": rec}
    finally:
        cur.close()
        con.close()
