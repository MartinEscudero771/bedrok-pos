# --------------------------------------------------
# HISTORIAL DE FACTURAS / TICKET / PDF
# --------------------------------------------------
from flask import render_template, request, redirect, url_for, flash, jsonify

from ..database import conectar
from ..services.recaudos import datos_ticket
from ..services.factus import enviar_nota_credito


def register(app):

    @app.route("/facturas")
    def listar_facturas():
        conexion = conectar()
        lista = []
        if conexion:
            cur = conexion.cursor(dictionary=True)
            try:
                cur.execute("""
                    SELECT f.*, c.nombres AS cliente_nombre, c.numero_documento
                    FROM facturas f JOIN clientes c ON f.id_cliente=c.id_cliente
                    ORDER BY f.id_factura DESC
                """)
                lista = cur.fetchall()
            finally:
                cur.close()
                conexion.close()
        return render_template("facturas.html", facturas=lista)

    @app.route("/facturas/pdf/<int:id_factura>")
    def descargar_pdf(id_factura):
        conexion = conectar()
        if not conexion:
            flash("No fue posible conectar con la base de datos.", "error")
            return redirect(url_for("listar_facturas"))
        cur = conexion.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM facturas WHERE id_factura=%s", (id_factura,))
            factura = cur.fetchone()
            if factura and factura.get("url_pdf"):
                return redirect(factura["url_pdf"])
            flash("La factura no tiene URL de PDF asociada.", "error")
        except Exception as e:
            flash(f"Ocurrió un error: {e}", "error")
        finally:
            cur.close()
            conexion.close()
        return redirect(url_for("listar_facturas"))

    @app.route("/ticket/<int:id_factura>")
    def ticket(id_factura):
        datos = datos_ticket(id_factura)
        if not datos:
            flash("Factura no encontrada.", "error")
            return redirect(url_for("pos"))
        return render_template("ticket.html", **datos)

    @app.route("/facturas/<int:id_factura>/nota-credito", methods=["POST"])
    def nota_credito(id_factura):
        """Opcional del reto: anular una factura electronica validada via nota credito."""
        import json as _json
        import uuid as _uuid
        from ..database import conectar as _conectar
        from flask import redirect as _redirect

        conexion = _conectar()
        if not conexion:
            flash("No fue posible conectar con la base de datos.", "error")
            return _redirect(url_for("listar_facturas"))
        cur = conexion.cursor(dictionary=True)
        try:
            cur.execute("""
                SELECT f.*, c.tipo_documento, c.numero_documento, c.nombres AS cliente_nombre,
                       c.direccion, c.correo, c.telefono, c.codigo_organizacion, c.codigo_tributo,
                       c.codigo_pais, c.codigo_municipio
                FROM facturas f JOIN clientes c ON c.id_cliente=f.id_cliente
                WHERE f.id_factura=%s
            """, (id_factura,))
            fac = cur.fetchone()
            if not fac or fac["estado"] != "VALIDADA" or not fac.get("numero_factura"):
                flash("Solo se puede generar nota credito de una factura VALIDADA ante la DIAN.", "error")
                return _redirect(url_for("listar_facturas"))
            cur.execute("""
                SELECT d.*, p.codigo_referencia, p.nombre, p.codigo_unidad, p.codigo_estandar, p.porcentaje_iva
                FROM detalle_factura d JOIN productos p ON p.id_producto=d.id_producto
                WHERE d.id_factura=%s
            """, (id_factura,))
            detalle = cur.fetchall()
            if not detalle:
                flash("La factura no tiene detalle disponible.", "error")
                return _redirect(url_for("listar_facturas"))
            items = [{
                "note": f"Anulacion de la linea {d['nombre']}",
                "code_reference": d["codigo_referencia"],
                "name": d["nombre"],
                "quantity": f"{d['cantidad']:.2f}",
                "discount_rate": "0.00",
                "price": f"{d['precio_unitario']:.2f}",
                "unit_measure_code": d["codigo_unidad"] or "94",
                "standard_code": d["codigo_estandar"] or "999",
                "taxes": [{"code": "01", "rate": f"{d['porcentaje_iva']:.2f}"}],
            } for d in detalle]
            payload = {
                "reference_code": "NC-BEDROK-" + _uuid.uuid4().hex[:8].upper(),
                "correction_concept_code": "1",
                "numbering_range_id": 390,
                "bill_number": fac["numero_factura"],
                "customer": {
                    "identification_document_code": fac["tipo_documento"],
                    "identification": fac["numero_documento"],
                    "names": fac["cliente_nombre"],
                    "address": fac["direccion"] or "Sin direccion",
                    "email": fac["correo"] or "sincorreo@example.com",
                    "phone": fac["telefono"] or "3000000000",
                    "legal_organization_code": fac.get("codigo_organizacion") or "2",
                    "tribute_code": fac.get("codigo_tributo") or "ZZ",
                    "country_code": fac.get("codigo_pais") or "CO",
                    "municipality_code": fac.get("codigo_municipio") or "23001",
                    "responsibilities": ["R-99-PN"],
                },
                "payment_details": [{
                    "payment_form": "1",
                    "payment_method_code": "10",
                    "amount": f"{float(fac['total']):.2f}",
                }],
                "observation": "Nota credito generada por el POS Bedrok para anular la factura",
                "items": items,
            }
            status, resp = enviar_nota_credito(payload)
            ok = status in (200, 201)
            data = (resp or {}).get("data") or {}
            numero_nc = (data.get("number") or data.get("document_number")
                         or (data.get("credit_note") or {}).get("number"))
            cur.execute("""
                INSERT INTO respuestas_factus
                (id_factura, codigo_referencia, codigo_http, estado_api, mensaje, solicitud_json, respuesta_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (id_factura, fac["codigo_referencia"], status,
                  "NC_EXITOSO" if ok else "NC_ERROR",
                  str((resp or {}).get("message", ""))[:500],
                  _json.dumps(payload)[:60000], _json.dumps(resp)[:60000]))
            conexion.commit()
            if ok:
                flash(f"Nota credito generada correctamente: {numero_nc or payload['reference_code']}. "
                      "La factura queda anulada ante la DIAN.", "success")
            else:
                flash(f"Factus rechazo la nota credito ({status}): "
                      f"{str((resp or {}).get('message'))}", "error")
        finally:
            cur.close()
            conexion.close()
        return _redirect(url_for("listar_facturas"))

    @app.route("/api/factura/<int:id_factura>/ticket-data")
    def ticket_data(id_factura):
        datos = datos_ticket(id_factura)
        if not datos:
            return jsonify({"success": False}), 404
        f = datos["factura"]
        r = datos["recaudo"]
        return jsonify({
            "success": True,
            "ticket_url": url_for("ticket", id_factura=id_factura),
            "pdf_url": f.get("url_pdf"),
            "cufe": f.get("cufe"),
            "numero_factura": f.get("numero_factura"),
            "pay_status": f.get("pay_status"),
            "pay_reference": f.get("pay_reference"),
            "pay_qr": (r or {}).get("qr") if r else None,
            "breb_key": (r or {}).get("breb_key") if r else None,
        })
