# --------------------------------------------------
# PRODUCTOS
# --------------------------------------------------
import re
from decimal import Decimal, InvalidOperation

import mysql.connector
from flask import render_template, request, redirect, url_for, flash

from ..database import conectar

IVA_VALIDOS = {"0", "5", "19"}


def register(app):

    @app.route("/productos", methods=["GET", "POST"])
    def productos():
        if request.method == "POST":
            codigo = request.form.get("codigo_referencia", "").strip()
            nombre = request.form.get("nombre", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            precio = request.form.get("precio", "").strip()
            iva = request.form.get("porcentaje_iva", "").strip()
            stock = request.form.get("stock", "").strip()

            if not codigo or not nombre or not precio or not iva or not stock:
                flash("Completa los campos obligatorios.", "error")
                return redirect(url_for("productos"))
            if not re.fullmatch(r"[A-Za-z0-9_\-]{2,50}", codigo):
                flash("El codigo debe tener entre 2 y 50 caracteres (letras, numeros, guion o guion bajo).", "error")
                return redirect(url_for("productos"))
            if len(nombre) < 2 or len(nombre) > 150:
                flash("El nombre del producto debe tener entre 2 y 150 caracteres.", "error")
                return redirect(url_for("productos"))
            if len(descripcion) > 250:
                flash("La descripcion es demasiado larga.", "error")
                return redirect(url_for("productos"))
            if iva not in IVA_VALIDOS:
                flash("El IVA debe ser 0, 5 o 19.", "error")
                return redirect(url_for("productos"))
            try:
                precio_decimal = Decimal(precio)
                iva_decimal = Decimal(iva)
                stock_entero = int(stock)
            except (ValueError, ArithmeticError, InvalidOperation):
                flash("Revisa el precio, el IVA y el inventario.", "error")
                return redirect(url_for("productos"))
            if precio_decimal <= 0 or precio_decimal > Decimal("50000000"):
                flash("El precio debe ser mayor a 0 y menor a $50.000.000.", "error")
                return redirect(url_for("productos"))
            if stock_entero < 0 or stock_entero > 1000000:
                flash("El stock debe estar entre 0 y 1.000.000.", "error")
                return redirect(url_for("productos"))

            conexion = conectar()
            if not conexion:
                flash("No fue posible conectar con MySQL.", "error")
                return redirect(url_for("productos"))

            cursor = conexion.cursor()
            try:
                cursor.execute("""
                    INSERT INTO productos
                    (codigo_referencia, nombre, descripcion, precio, porcentaje_iva, stock)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (codigo, nombre, descripcion, precio_decimal, iva_decimal, stock_entero))
                conexion.commit()
                flash("Producto registrado correctamente.", "success")
            except mysql.connector.Error as error:
                conexion.rollback()
                if getattr(error, "errno", None) == 1062:
                    flash("Ya existe un producto con ese codigo de referencia.", "error")
                else:
                    flash(f"Error al registrar el producto: {error}", "error")
            finally:
                cursor.close()
                conexion.close()
            return redirect(url_for("productos"))

        conexion = conectar()
        lista = []
        if conexion:
            cur = conexion.cursor(dictionary=True)
            try:
                cur.execute("SELECT * FROM productos ORDER BY id_producto DESC")
                lista = cur.fetchall()
            finally:
                cur.close()
                conexion.close()
        return render_template("productos.html", productos=lista)
