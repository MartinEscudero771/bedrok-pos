# --------------------------------------------------
# PEDIDOS INTERNACIONALES
# Cobro en divisas (USD) con doble moneda Factus:
#   "currency": {"type": "USD", "exchange_rate": "..." }
# Documentado en developers.factus.com.co -> Con doble moneda
# --------------------------------------------------
import json
import uuid
import math
from decimal import Decimal, ROUND_HALF_UP

import mysql.connector
from flask import render_template, request, redirect, url_for, flash, jsonify

from ..database import conectar
from ..services.cambio import obtener_tasa_usd_cop
from ..services.factus import enviar_factura_a_factus
from ..services.recaudos import guardar_recaudo_db

IVA_VALIDOS = {"0", "5", "19"}


def register(app):

    @app.route("/pedidos")
    def pedidos():
        conexion = conectar()
        if not conexion:
            return "No fue posible conectar con MySQL.", 500
        cur = conexion.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM clientes WHERE activo=TRUE ORDER BY nombres")
            clientes = cur.fetchall()
            cur.execute("""
                SELECT * FROM productos
                WHERE activo=TRUE AND stock>0 AND porcentaje_iva IN (0,5,19)
                ORDER BY nombre
            """)
            productos = cur.fetchall()
        finally:
            cur.close()
            conexion.close()
        try:
            tasa = obtener_tasa_usd_cop()
        except Exception as e:
            tasa = {"tasa": None, "fuente": None, "fecha": None}
        return render_template("pedidos.html", clientes=clientes, productos=productos, tasa=tasa)

    @app.route("/api/tasa")
    def api_tasa():
        try:
            return jsonify({"success": True, **obtener_tasa_usd_cop()})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 502

    @app.route("/guardar-pedido", methods=["POST"])
    def guardar_pedido():
        conexion = conectar()
        if not conexion:
            return jsonify({"success": False, "mensaje": "No se pudo conectar con MySQL."}), 500
        cursor = conexion.cursor(dictionary=True)
        try:
            id_cliente = request.form.get("cliente")
            productos_json = request.form.get("productos_json", "[]")
            monto_usd = request.form.get("monto_usd", "").strip()

            if not id_cliente:
                raise ValueError("Selecciona el cliente del pedido.")
            try:
                id_cliente = int(id_cliente)
            except ValueError:
                raise ValueError("Cliente invalido.")
            if not monto_usd:
                raise ValueError("Ingresa el monto en dolares con el que paga el cliente.")
            try:
                monto_usd = float(monto_usd)
            except ValueError:
                raise ValueError("Monto en dolares invalido.")
            if monto_usd <= 0:
                raise ValueError("El monto en dolares debe ser mayor a 0.")
            try:
                productos = json.loads(productos_json)
            except (ValueError, json.JSONDecodeError):
                raise ValueError("Datos del pedido invalidos.")
            if not isinstance(productos, list) or not productos:
                raise ValueError("Agrega al menos un producto al pedido.")

            tasa_info = obtener_tasa_usd_cop()
            tasa = Decimal(str(tasa_info["tasa"]))

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
                cursor.execute("""
                    SELECT id_producto, codigo_referencia, nombre, precio,
                           porcentaje_iva, codigo_unidad, codigo_estandar, stock
                    FROM productos WHERE id_producto=%s AND activo=TRUE FOR UPDATE
                """, (id_producto,))
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

            if total > Decimal("12100000"):
                raise ValueError("El pedido supera el tope de Factus Pay/Factus ($12.100.000).")

            # Equivalencia en USD (se cobra en divisas)
            equivalente_usd = (total / tasa).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            entregado = Decimal(str(monto_usd)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if entregado < equivalente_usd:
                raise ValueError(
                    f"El monto entregado (US$ {entregado}) no cubre el pedido "
                    f"(US$ {equivalente_usd} al tasa {tasa}). Faltan US$ {equivalente_usd - entregado}."
                )
            cambio_usd = (entregado - equivalente_usd).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            cambio_cop = (cambio_usd * tasa).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            referencia = "BEDROK-INT-" + uuid.uuid4().hex[:8].upper()
            cursor.execute("""
                INSERT INTO facturas
                (id_cliente, codigo_referencia, fecha_emision, subtotal, total_iva, total,
                 estado, ambiente, metodo_pago, pay_status, moneda, tasa_cambio, monto_moneda, cambio_moneda)
                VALUES (%s,%s,NOW(),%s,%s,%s,'PENDIENTE','SANDBOX','INTERNACIONAL','EFECTIVO',
                        'USD',%s,%s,%s)
            """, (id_cliente, referencia, subtotal, total_iva, total, tasa, entregado, cambio_usd))
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
        except (mysql.connector.Error, KeyError, TypeError) as error:
            conexion.rollback()
            print("guardar_pedido BD:", error)
            return jsonify({"success": False, "mensaje": "Ocurrio un error al registrar el pedido."}), 500
        except Exception as error:
            conexion.rollback()
            print("guardar_pedido:", error)
            return jsonify({"success": False, "mensaje": str(error)}), 502
        finally:
            cursor.close()
            conexion.close()

        # ---- Factura electronica con doble moneda (Factus) ----
        factus_status = None
        respuesta_factus = {}
        try:
            payload = {
                "reference_code": referencia,
                "document": "01",
                "numbering_range_id": 389,
                "operation_type": "10",
                "send_email": False,
                "currency": {
                    "type": "USD",
                    "exchange_rate": f"{tasa:.2f}",
                },
                "observation": "Pedido internacional cobrado en USD",
                "payment_details": [{
                    "payment_form": "1",
                    "payment_method_code": "10",
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
            cur2.execute("""
                INSERT INTO respuestas_factus
                (id_factura, codigo_referencia, codigo_http, estado_api, mensaje, solicitud_json, respuesta_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (id_factura, referencia, factus_status, estado_api,
                  str((respuesta_factus or {}).get("message", "Procesado por Factus"))[:500],
                  json.dumps(payload)[:60000], json.dumps(respuesta_factus)[:60000]))
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
            print("Factus (pedido):", e)
            respuesta_factus = {"message": str(e)}

        return jsonify({
            "success": True,
            "mensaje": "Pedido internacional registrado.",
            "id_factura": id_factura,
            "referencia": referencia,
            "total": float(total),
            "moneda": "USD",
            "tasa": float(tasa),
            "equivalente_usd": float(equivalente_usd),
            "entregado_usd": float(entregado),
            "cambio_usd": float(cambio_usd),
            "cambio_cop": float(cambio_cop),
            "factus_status": factus_status,
            "ticket_url": url_for("ticket", id_factura=id_factura),
        })
