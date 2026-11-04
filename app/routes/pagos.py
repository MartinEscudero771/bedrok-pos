# --------------------------------------------------
# COBRO: guardar POS/factura + Factus + QR Bre-B Factus Pay
# API de recaudos + webhook + salud
# --------------------------------------------------
import hmac
import json
import uuid
import threading
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import mysql.connector
from flask import request, redirect, url_for, flash, jsonify

from ..database import conectar
from ..services.factus import enviar_factura_a_factus
from ..services.factus_pay import crear_recaudo, consultar_recaudo
from ..services.recaudos import guardar_recaudo_db

_cobro_previo_lock = threading.Lock()

FACTUS_PAY_WEBHOOK_KEY = ""

def _webhook_key():
    import os
    return os.getenv("FACTUS_PAY_WEBHOOK_KEY", "").strip()


def _armar_payload_factus(referencia, cliente_info, items_factus, total, metodo_pago):
    return {
        "reference_code": referencia,
        "document": "01",
        "numbering_range_id": 389,
        "operation_type": "10",
        "send_email": False,
        "payment_details": [{
            "payment_form": "1",
            "payment_method_code": "10" if metodo_pago == "EFECTIVO" else "42",
            "amount": f"{total:.2f}",
        }],
        "customer": {
            "identification_document_code": cliente_info["tipo_documento"],
            "identification": cliente_info["numero_documento"],
            "names": cliente_info["nombres"],
            "address": cliente_info["direccion"] or "Sin direccion",
            "email": cliente_info["correo"] or "sincorreo@example.com",
            "phone": cliente_info["telefono"] or "3000000000",
            "legal_organization_code": cliente_info.get("codigo_organizacion") or "2",
            "tribute_code": cliente_info.get("codigo_tributo") or "ZZ",
            "country_code": cliente_info.get("codigo_pais") or "CO",
            "municipality_code": cliente_info.get("codigo_municipio") or "23001",
            "responsibilities": ["R-99-PN"],
        },
        "items": items_factus,
    }


def _emitir_cobro_previo(reference_code):
    """Emite la factura DIAN pendiente de un cobro previo ya pagado (Flujo A)."""
    with _cobro_previo_lock:
        con = conectar()
        if not con:
            return {"emitida": False, "error": "sin BD"}
        cur = con.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT * FROM facturas WHERE codigo_referencia=%s OR pay_reference=%s LIMIT 1 FOR UPDATE",
                (reference_code, reference_code),
            )
            fac = cur.fetchone()
            if not fac or fac["estado"] != "COBRO_PREVIO" or fac.get("cufe"):
                return {"emitida": False, "razon": "no aplica"}
            cur.execute(
                "SELECT solicitud_json FROM respuestas_factus"
                " WHERE id_factura=%s AND estado_api='PEND_ENVIO' LIMIT 1",
                (fac["id_factura"],),
            )
            row = cur.fetchone()
            if not row:
                return {"emitida": False, "error": "sin payload"}
            payload = json.loads(row["solicitud_json"])
            status, respuesta = enviar_factura_a_factus(payload)
            ok = status in (200, 201)
            cur.execute("""
                INSERT INTO respuestas_factus
                (id_factura, codigo_referencia, codigo_http, estado_api, mensaje, solicitud_json, respuesta_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (fac["id_factura"], reference_code, status,
                  "EXITOSO" if ok else "ERROR",
                  str((respuesta or {}).get("message", ""))[:500],
                  json.dumps(payload)[:60000], json.dumps(respuesta)[:60000]))
            if ok:
                data = (respuesta or {}).get("data", {})
                bill = data.get("bill", {}) or {}
                cufe = bill.get("cufe") or bill.get("uuid") or data.get("cufe") or data.get("uuid")
                numf = (bill.get("number") or bill.get("document_number")
                        or data.get("number") or data.get("document_number"))
                links = data.get("links", {}) or {}
                pdf_url = links.get("public_url") or links.get("qr")
                cur.execute(
                    "UPDATE facturas SET estado='VALIDADA', cufe=%s, numero_factura=%s, url_pdf=%s"
                    " WHERE id_factura=%s",
                    (cufe, numf, pdf_url, fac["id_factura"]),
                )
                cur.execute("""
                    UPDATE productos p JOIN detalle_factura d ON d.id_producto=p.id_producto
                    SET p.stock = p.stock - d.cantidad
                    WHERE d.id_factura=%s
                """, (fac["id_factura"],))
                cur.execute(
                    "UPDATE respuestas_factus SET estado_api='ENVIADO'"
                    " WHERE id_factura=%s AND estado_api='PEND_ENVIO'",
                    (fac["id_factura"],),
                )
                con.commit()
                return {"emitida": True, "numero_factura": numf, "estado": "VALIDADA"}
            con.commit()
            return {"emitida": False, "http": status, "mensaje": (respuesta or {}).get("message")}
        finally:
            cur.close()
            con.close()


def _estadisticas_conciliacion():
    con = conectar()
    if not con:
        return None
    cur = con.cursor(dictionary=True)
    try:
        out = {}
        cur.execute("""
            SELECT COUNT(*) AS c,
                   COALESCE(SUM(CASE WHEN f.estado='VALIDADA' THEN f.total END),0) AS monto,
                   SUM(f.estado='VALIDADA') AS valid
            FROM facturas f WHERE DATE(f.fecha_emision)=CURDATE()
        """)
        row = cur.fetchone()
        out["ventas_hoy"] = row["c"]
        out["validadas_hoy"] = int(row["valid"] or 0)
        out["monto_facturado_hoy"] = float(row["monto"] or 0)
        cur.execute("""
            SELECT COUNT(*) AS c, COALESCE(SUM(r.amount),0) AS monto
            FROM recaudos_pay r WHERE r.status='paid' AND DATE(r.creado_en)=CURDATE()
        """)
        row = cur.fetchone()
        out["pagos_hoy"] = row["c"]
        out["monto_recaudado_hoy"] = float(row["monto"] or 0)
        cur.execute("SELECT COUNT(*) AS c FROM facturas WHERE estado='COBRO_PREVIO'")
        out["por_facturar"] = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM respuestas_factus WHERE estado_api='NC_EXITOSO'")
        out["notas_credito"] = cur.fetchone()["c"]
        cur.execute("""
            SELECT COUNT(*) AS c FROM recaudos_pay
            WHERE status='ready' AND DATE(creado_en)=CURDATE()
        """)
        out["qr_pendientes_hoy"] = cur.fetchone()["c"]
        return out
    finally:
        cur.close()
        con.close()


def register(app):

    @app.route("/guardar-factura", methods=["POST"])
    def guardar_factura():
        conexion = conectar()
        if not conexion:
            return jsonify({"success": False, "mensaje": "No se pudo conectar con MySQL."}), 500
        cursor = conexion.cursor(dictionary=True)
        try:
            id_cliente = request.form.get("cliente")
            productos_json = request.form.get("productos_json", "[]")
            metodo_pago = (request.form.get("metodo_pago") or "EFECTIVO").strip().upper()
            if metodo_pago not in ("EFECTIVO", "BREB", "QR", "FACTUS_PAY"):
                metodo_pago = "EFECTIVO"
            if metodo_pago in ("QR", "FACTUS_PAY"):
                metodo_pago = "BREB"

            monto_recibido = None
            if metodo_pago == "EFECTIVO":
                raw = (request.form.get("monto_recibido") or "").strip()
                try:
                    monto_recibido = Decimal(str(raw)) if raw else None
                except Exception:
                    monto_recibido = None
                if monto_recibido is None or monto_recibido <= 0:
                    return jsonify({"success": False,
                                    "mensaje": "Ingresa el monto con el que paga el cliente (efectivo recibido)."}), 400
            try:
                expiration = int(request.form.get("expiration") or 86400)
            except ValueError:
                expiration = 86400
            expiration = max(300, min(expiration, 7 * 86400))

            if not id_cliente:
                raise ValueError("Selecciona un cliente.")
            try:
                id_cliente = int(id_cliente)
                productos = json.loads(productos_json)
            except (ValueError, json.JSONDecodeError):
                raise ValueError("Los datos enviados no son válidos.")
            if not isinstance(productos, list) or not productos:
                raise ValueError("Agrega al menos un producto.")

            conexion.start_transaction()
            cursor.execute(
                "SELECT * FROM clientes WHERE id_cliente=%s AND activo=TRUE", (id_cliente,)
            )
            cliente_info = cursor.fetchone()
            if not cliente_info:
                raise ValueError("El cliente seleccionado no existe o está inactivo.")

            cantidades = {}
            for item in productos:
                if not isinstance(item, dict):
                    raise ValueError("Hay un producto con datos incorrectos.")
                pid = int(item["id"])
                cant = int(item["cantidad"])
                if pid <= 0 or cant <= 0 or cant > 999:
                    raise ValueError("Productos y cantidades deben ser positivos.")
                cantidades[pid] = cantidades.get(pid, 0) + cant

            subtotal = Decimal("0.00")
            total_iva = Decimal("0.00")
            detalles = []
            items_factus = []
            for id_producto, cantidad in cantidades.items():
                cursor.execute("""
                    SELECT id_producto, codigo_referencia, nombre, precio,
                           porcentaje_iva, codigo_unidad, codigo_estandar, stock
                    FROM productos WHERE id_producto=%s AND activo=TRUE FOR UPDATE
                """, (id_producto,))
                prod = cursor.fetchone()
                if not prod:
                    raise ValueError("Uno de los productos no existe o está inactivo.")
                if cantidad > prod["stock"]:
                    raise ValueError(
                        f"Inventario insuficiente para {prod['nombre']}. Disponible: {prod['stock']}."
                    )
                precio = Decimal(str(prod["precio"]))
                piva = Decimal(str(prod["porcentaje_iva"]))
                base = (precio * cantidad).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                imp = (base * piva / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                subtotal += base
                total_iva += imp
                detalles.append({"id_producto": id_producto, "cantidad": cantidad, "precio": precio,
                                 "iva": piva, "valor_iva": imp, "subtotal": base, "total": base + imp})
                items_factus.append({
                    "code_reference": prod["codigo_referencia"],
                    "name": prod["nombre"],
                    "quantity": f"{cantidad:.2f}",
                    "discount_rate": "0.00",
                    "price": f"{precio:.2f}",
                    "unit_measure_code": prod["codigo_unidad"] or "94",
                    "standard_code": prod["codigo_estandar"] or "999",
                    "taxes": [{"code": "01", "rate": f"{piva:.2f}"}],
                })
            total = subtotal + total_iva
            if metodo_pago == "EFECTIVO" and monto_recibido is not None and monto_recibido < total:
                return jsonify({"success": False,
                                "mensaje": (f"El monto recibido (${monto_recibido:,.2f}) no cubre el total "
                                            f"(${total:,.2f}) del comprobante.")}), 400
            referencia = "BEDROK-" + uuid.uuid4().hex[:12].upper()
            cursor.execute("""
                INSERT INTO facturas
                (id_cliente, codigo_referencia, fecha_emision, subtotal, total_iva, total,
                 estado, ambiente, metodo_pago, pay_status)
                VALUES (%s,%s,NOW(),%s,%s,%s,'PENDIENTE','SANDBOX',%s,'SIN_QR')
            """, (id_cliente, referencia, subtotal, total_iva, total, metodo_pago))
            id_factura = cursor.lastrowid
            for d in detalles:
                cursor.execute("""
                    INSERT INTO detalle_factura
                    (id_factura, id_producto, cantidad, precio_unitario, porcentaje_iva, valor_iva, subtotal, total)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (id_factura, d["id_producto"], d["cantidad"], d["precio"], d["iva"],
                      d["valor_iva"], d["subtotal"], d["total"]))
                cursor.execute("UPDATE productos SET stock = stock - %s WHERE id_producto=%s",
                               (d["cantidad"], d["id_producto"]))
            conexion.commit()
        except ValueError as error:
            conexion.rollback()
            return jsonify({"success": False, "mensaje": str(error)}), 400
        except (mysql.connector.Error, KeyError, TypeError, InvalidOperation) as error:
            conexion.rollback()
            print("Error al guardar factura en BD:", error)
            return jsonify({"success": False, "mensaje": "Ocurrió un error al guardar la factura."}), 500
        finally:
            cursor.close()
            conexion.close()

        # ---- ENVÍO A FACTUS (factura electrónica) ----
        factus_status = None
        respuesta_factus = {}
        try:
            payload = {
                "reference_code": referencia,
                "document": "01",
                "numbering_range_id": 389,
                "operation_type": "10",
                "send_email": False,
                "payment_details": [{
                    "payment_form": "1",
                    "payment_method_code": "10" if metodo_pago == "EFECTIVO" else "42",
                    "amount": f"{total:.2f}",
                }],
                "customer": {
                    "identification_document_code": cliente_info["tipo_documento"],
                    "identification": cliente_info["numero_documento"],
                    "names": cliente_info["nombres"],
                    "address": cliente_info["direccion"] or "Sin direccion",
                    "email": cliente_info["correo"] or "sincorreo@example.com",
                    "phone": cliente_info["telefono"] or "3000000000",
                    "legal_organization_code": cliente_info.get("codigo_organizacion") or "2",
                    "tribute_code": cliente_info.get("codigo_tributo") or "ZZ",
                    "country_code": cliente_info.get("codigo_pais") or "CO",
                    "municipality_code": cliente_info.get("codigo_municipio") or "23001",
                    "responsibilities": ["R-99-PN"],
                },
                "items": items_factus,
            }
            factus_status, respuesta_factus = enviar_factura_a_factus(payload)
            con2 = conectar()
            cur2 = con2.cursor()
            estado_api = "EXITOSO" if factus_status in (200, 201) else "ERROR"
            mensaje_api = str((respuesta_factus or {}).get("message", "Procesado por Factus"))
            cur2.execute("""
                INSERT INTO respuestas_factus
                (id_factura, codigo_referencia, codigo_http, estado_api, mensaje, solicitud_json, respuesta_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (id_factura, referencia, factus_status, estado_api, mensaje_api[:500],
                  json.dumps(payload), json.dumps(respuesta_factus)[:60000]))
            if factus_status in (200, 201):
                data = (respuesta_factus or {}).get("data", {})
                bill = data.get("bill", {}) or {}
                cufe = bill.get("cufe") or bill.get("uuid") or data.get("cufe") or data.get("uuid")
                numf = (bill.get("number") or bill.get("document_number")
                        or data.get("number") or data.get("document_number"))
                links = data.get("links", {}) or {}
                pdf_url = links.get("public_url") or links.get("qr")
                cur2.execute(
                    "UPDATE facturas SET estado='VALIDADA', cufe=%s, numero_factura=%s, url_pdf=%s"
                    " WHERE id_factura=%s",
                    (cufe, numf, pdf_url, id_factura),
                )
            con2.commit()
            cur2.close()
            con2.close()
        except Exception as e:
            print("Factus:", e)
            factus_status = factus_status or 500
            respuesta_factus = respuesta_factus or {"message": str(e)}

        # ---- FACTUS PAY (QR Bre-B) ----
        pay_info = {"status": "no_aplica", "qr": None, "breb_key": None, "qr_expires_at": None}
        if metodo_pago == "BREB":
            try:
                http_pay, json_pay = crear_recaudo(referencia, float(total), expiration)
                norm = guardar_recaudo_db(id_factura, referencia, float(total), http_pay, json_pay)
                pay_info = {"status": norm["status"], "qr": norm["qr"], "breb_key": norm["breb_key"],
                            "qr_expires_at": norm["qr_expires_at"],
                            "raw_message": (json_pay or {}).get("message"), "http": http_pay}
            except Exception as e:
                print("Factus Pay:", e)
                pay_info = {"status": "error", "qr": None, "mensaje": str(e)}
        else:
            try:
                c = conectar()
                cc = c.cursor()
                cc.execute("UPDATE facturas SET pay_status='EFECTIVO' WHERE id_factura=%s", (id_factura,))
                c.commit()
                cc.close()
                c.close()
            except Exception:
                pass

        return jsonify({
            "success": True,
            "mensaje": "Venta POS registrada." + (" QR Bre-B generado." if pay_info.get("qr") else ""),
            "id_factura": id_factura,
            "referencia": referencia,
            "total": float(total),
            "metodo_pago": metodo_pago,
            "factus_status": factus_status,
            "respuesta_factus": respuesta_factus,
            "pay": pay_info,
            "ticket_url": url_for("ticket", id_factura=id_factura),
        })

    @app.route("/crear-cobro-previo", methods=["POST"])
    def crear_cobro_previo():
        """Flujo A del reto: generar recaudo Bre-B primero; la factura DIAN se
        emite automaticamente cuando el pago se confirma (polling o conciliacion)."""
        conexion = conectar()
        if not conexion:
            return jsonify({"success": False, "mensaje": "No se pudo conectar con MySQL."}), 500
        cursor = conexion.cursor(dictionary=True)
        try:
            id_cliente = request.form.get("cliente")
            productos_json = request.form.get("productos_json", "[]")
            try:
                expiration = int(request.form.get("expiration") or 86400)
            except ValueError:
                expiration = 86400
            expiration = max(300, min(expiration, 7 * 86400))

            if not id_cliente:
                return jsonify({"success": False, "mensaje": "Selecciona el cliente de la venta."}), 400
            try:
                id_cliente = int(id_cliente)
                productos = json.loads(productos_json)
            except (ValueError, json.JSONDecodeError):
                return jsonify({"success": False, "mensaje": "Datos invalidos."}), 400
            if not isinstance(productos, list) or not productos:
                return jsonify({"success": False, "mensaje": "Agrega al menos un producto."}), 400

            conexion.start_transaction()
            cursor.execute(
                "SELECT * FROM clientes WHERE id_cliente=%s AND activo=TRUE", (id_cliente,)
            )
            cliente_info = cursor.fetchone()
            if not cliente_info:
                raise ValueError("El cliente seleccionado no existe o esta inactivo.")

            cantidades = {}
            for item in productos:
                if not isinstance(item, dict):
                    raise ValueError("Producto con datos incorrectos.")
                try:
                    pid = int(item["id"])
                    cant = int(item["cantidad"])
                except (KeyError, ValueError):
                    raise ValueError("Producto con datos incorrectos.")
                if pid <= 0 or cant <= 0 or cant > 999:
                    raise ValueError("Productos y cantidades deben ser positivos.")
                cantidades[pid] = cantidades.get(pid, 0) + cant

            subtotal = Decimal("0.00")
            total_iva = Decimal("0.00")
            detalles = []
            items_factus = []
            for id_producto, cantidad in cantidades.items():
                cursor.execute(
                    "SELECT * FROM productos WHERE id_producto=%s AND activo=TRUE FOR UPDATE",
                    (id_producto,),
                )
                prod = cursor.fetchone()
                if not prod:
                    raise ValueError("Uno de los productos no existe o esta inactivo.")
                if cantidad > prod["stock"]:
                    raise ValueError(
                        f"Stock insuficiente para {prod['nombre']}. Disponible: {prod['stock']}."
                    )
                precio = Decimal(str(prod["precio"]))
                piva = Decimal(str(prod["porcentaje_iva"]))
                base = (precio * cantidad).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                imp = (base * piva / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                subtotal += base
                total_iva += imp
                detalles.append({"id_producto": id_producto, "cantidad": cantidad, "precio": precio,
                                 "iva": piva, "valor_iva": imp, "subtotal": base, "total": base + imp})
                items_factus.append({
                    "code_reference": prod["codigo_referencia"],
                    "name": prod["nombre"],
                    "quantity": f"{cantidad:.2f}",
                    "discount_rate": "0.00",
                    "price": f"{precio:.2f}",
                    "unit_measure_code": prod["codigo_unidad"] or "94",
                    "standard_code": prod["codigo_estandar"] or "999",
                    "taxes": [{"code": "01", "rate": f"{piva:.2f}"}],
                })
            total = subtotal + total_iva
            if total < Decimal("10000"):
                raise ValueError(
                    f"El total (${total:,.2f}) es menor al minimo de Factus Pay ($10.000). Usa Efectivo."
                )
            referencia = "BEDROK-" + uuid.uuid4().hex[:12].upper()
            payload_factus = _armar_payload_factus(referencia, cliente_info, items_factus, total, "BREB")
            cursor.execute("""
                INSERT INTO facturas
                (id_cliente, codigo_referencia, fecha_emision, subtotal, total_iva, total,
                 estado, ambiente, metodo_pago, pay_status)
                VALUES (%s,%s,NOW(),%s,%s,%s,'COBRO_PREVIO','SANDBOX','BREB','SIN_QR')
            """, (id_cliente, referencia, subtotal, total_iva, total))
            id_factura = cursor.lastrowid
            for d in detalles:
                cursor.execute("""
                    INSERT INTO detalle_factura
                    (id_factura, id_producto, cantidad, precio_unitario, porcentaje_iva, valor_iva, subtotal, total)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (id_factura, d["id_producto"], d["cantidad"], d["precio"], d["iva"],
                      d["valor_iva"], d["subtotal"], d["total"]))
            cursor.execute("""
                INSERT INTO respuestas_factus
                (id_factura, codigo_referencia, codigo_http, estado_api, mensaje, solicitud_json, respuesta_json)
                VALUES (%s,%s,0,'PEND_ENVIO','Cobro previo pendiente de pago',%s,'{}')
            """, (id_factura, referencia, json.dumps(payload_factus)[:60000]))
            conexion.commit()
        except ValueError as error:
            conexion.rollback()
            return jsonify({"success": False, "mensaje": str(error)}), 400
        except (mysql.connector.Error, KeyError, TypeError, InvalidOperation) as error:
            conexion.rollback()
            print("crear_cobro_previo BD:", error)
            return jsonify({"success": False, "mensaje": "Ocurrio un error al crear el recaudo."}), 500
        finally:
            cursor.close()
            conexion.close()

        http_pay, json_pay = crear_recaudo(referencia, float(total), expiration)
        norm = guardar_recaudo_db(id_factura, referencia, float(total), http_pay, json_pay)
        pay_info = {"status": norm["status"], "qr": norm["qr"], "breb_key": norm["breb_key"],
                    "qr_expires_at": norm["qr_expires_at"], "http": http_pay,
                    "raw_message": (json_pay or {}).get("message")}
        return jsonify({
            "success": True,
            "flujo": "A",
            "mensaje": ("Recaudo Bre-B creado. La factura DIAN se emite sola al confirmar el pago."
                        if pay_info.get("qr") else (json_pay or {}).get("message", "Recaudo no creado.")),
            "id_factura": id_factura,
            "referencia": referencia,
            "total": float(total),
            "metodo_pago": "BREB",
            "pay": pay_info,
            "ticket_url": url_for("ticket", id_factura=id_factura),
        })

    @app.route("/api/recaudo/<reference_code>")
    def api_recaudo(reference_code):
        http_pay, json_pay = consultar_recaudo(reference_code)
        data = (json_pay or {}).get("data") or {}
        try:
            con = conectar()
            if con:
                cur = con.cursor(dictionary=True)
                cur.execute(
                    "SELECT id_factura, estado FROM facturas WHERE codigo_referencia=%s OR pay_reference=%s LIMIT 1",
                    (reference_code, reference_code),
                )
                row = cur.fetchone()
                cur.close()
                con.close()
                idf = row["id_factura"] if row else None
                norm = guardar_recaudo_db(idf, reference_code, data.get("amount") or 0, http_pay, json_pay)
            else:
                norm = {"status": str(data.get("status") or "desconocido"),
                        "qr": data.get("qr"), "breb_key": data.get("breb_key"),
                        "qr_expires_at": data.get("qr_expires_at"),
                        "collected_at": data.get("collected_at")}
        except Exception as e:
            print("api_recaudo db:", e)
            norm = {"status": str(data.get("status") or "desconocido"),
                    "qr": data.get("qr"), "breb_key": data.get("breb_key"),
                    "qr_expires_at": data.get("qr_expires_at"),
                    "collected_at": data.get("collected_at")}
        factura_info = None
        debe_emitir = (
            str(norm.get("status")).lower() == "paid"
            or (row is not None and row.get("estado") == "COBRO_PREVIO"
                and row.get("pay_status") == "PAGADO")
        )
        if debe_emitir:
            try:
                factura_info = _emitir_cobro_previo(reference_code)
            except Exception as e:
                print("emitir cobro previo:", e)
                factura_info = {"emitida": False, "error": str(e)}
        return jsonify({"http": http_pay, "pay": norm, "factura": factura_info, "raw": json_pay})

    @app.route("/api/conciliacion")
    def api_conciliacion():
        return jsonify({"success": True, "stats": _estadisticas_conciliacion()})

    @app.route("/api/conciliar", methods=["POST"])
    def api_conciliar():
        """Mantenimiento: marca pagados (Leer Factus Pay) y emite cobros previos pendientes."""
        con = conectar()
        refs = []
        if con:
            cur = con.cursor(dictionary=True)
            cur.execute("""
                SELECT reference_code FROM recaudos_pay
                WHERE status IN ('ready','paid')
                ORDER BY id_recaudo DESC LIMIT 100
            """)
            refs = [r["reference_code"] for r in cur.fetchall()]
            cur.close()
            con.close()
        emitidas, pagados, errores = 0, 0, []
        for ref in refs:
            try:
                http_pay, json_pay = consultar_recaudo(ref)
                data = (json_pay or {}).get("data") or {}
                st = str(data.get("status") or "").lower()
                if st not in ("paid", "ready"):
                    continue
                con2 = conectar()
                cur2 = con2.cursor(dictionary=True)
                cur2.execute(
                    "SELECT id_factura FROM facturas WHERE codigo_referencia=%s OR pay_reference=%s LIMIT 1",
                    (ref, ref),
                )
                frow = cur2.fetchone()
                cur2.close()
                con2.close()
                guardar_recaudo_db(frow["id_factura"] if frow else None, ref,
                                   data.get("amount") or 0, http_pay, json_pay)
                if st == "paid":
                    pagados += 1
                    info = _emitir_cobro_previo(ref)
                    if info.get("emitida"):
                        emitidas += 1
                    elif info and info.get("error"):
                        errores.append(f"{ref}: {info.get('error')}")
            except Exception as e:
                errores.append(f"{ref}: {e}")
        return jsonify({"success": True, "pagados": pagados, "emitidas": emitidas,
                        "errores": errores[:10], "stats": _estadisticas_conciliacion()})


    @app.route("/webhooks/factus-pay", methods=["POST"])
    def webhook_factus_pay():
        key = (request.args.get("key") or "").strip()
        wk = _webhook_key()
        if wk:
            if not key or not hmac.compare_digest(key, wk):
                return jsonify({"received": False, "error": "key inválida"}), 401
        try:
            body = request.get_json(force=True, silent=True) or {}
        except Exception:
            body = {}
        data = body.get("data") or body
        ref = str(data.get("reference_code") or "").strip()
        status = str(data.get("status") or "").strip().lower()
        amount = data.get("amount")
        payer = data.get("payer")
        resultado = "sin-referencia"
        if ref:
            try:
                con = conectar()
                cur = con.cursor(dictionary=True)
                cur.execute(
                    "SELECT id_factura, total FROM facturas WHERE codigo_referencia=%s OR pay_reference=%s LIMIT 1",
                    (ref, ref),
                )
                fac = cur.fetchone()
                if not fac:
                    resultado = "factura-no-encontrada"
                elif amount is not None and abs(float(amount) - float(fac["total"])) > Decimal("1"):
                    resultado = "monto-no-coincide"
                    cur.execute("INSERT INTO webhook_logs (reference_code, payload, resultado) VALUES (%s,%s,%s)",
                                (ref, json.dumps(body)[:60000], resultado))
                    con.commit()
                else:
                    cur.execute("""
                        INSERT INTO recaudos_pay (id_factura, reference_code, amount, status, payer_json, raw_json)
                        VALUES (%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE status=VALUES(status), payer_json=VALUES(payer_json),
                            raw_json=VALUES(raw_json), id_factura=VALUES(id_factura)
                    """, (fac["id_factura"], ref, float(amount or 0), status or "paid",
                          json.dumps(payer) if payer else None, json.dumps(body)[:60000]))
                    if status == "paid":
                        cur.execute("UPDATE facturas SET pay_status='PAGADO' WHERE id_factura=%s",
                                    (fac["id_factura"],))
                        resultado = "pagado-ok"
                    else:
                        resultado = f"estado-{status}"
                    cur.execute("INSERT INTO webhook_logs (reference_code, payload, resultado) VALUES (%s,%s,%s)",
                                (ref, json.dumps(body)[:60000], resultado))
                    con.commit()
                cur.close()
                con.close()
            except Exception as e:
                print("webhook:", e)
                resultado = f"error: {e}"
        else:
            try:
                con = conectar()
                cur = con.cursor()
                cur.execute("INSERT INTO webhook_logs (reference_code, payload, resultado) VALUES (%s,%s,%s)",
                            (None, json.dumps(body)[:60000], resultado))
                con.commit()
                cur.close()
                con.close()
            except Exception:
                pass
        return jsonify({"received": True, "resultado": resultado}), 200

    @app.route("/api/recaudos-local")
    def api_recaudos_local():
        con = conectar()
        if not con:
            return jsonify({"success": False}), 500
        cur = con.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM recaudos_pay ORDER BY id_recaudo DESC LIMIT 50")
            rows = cur.fetchall()
            for r in rows:
                if r.get("qr"):
                    r["qr"] = (r["qr"][:60] + "...[qr-base64]") if len(r["qr"]) > 60 else r["qr"]
            return jsonify({"success": True, "recaudos": rows})
        finally:
            cur.close()
            con.close()

    @app.route("/salud")
    def salud():
        from ..services.factus_pay import BASE_URL
        ok = conectar() is not None
        if ok:
            try:
                conectar().close()
            except Exception:
                pass
        return jsonify({"ok": ok, "factus_pay_base": BASE_URL})
