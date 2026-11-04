# --------------------------------------------------
# CLIENTES
# --------------------------------------------------
import re

import mysql.connector
from flask import render_template, request, redirect, url_for, flash

from ..database import conectar

TIPOS_DOC_VALIDOS = {"13", "31", "22", "41"}


def register(app):

    @app.route("/clientes", methods=["GET", "POST"])
    def clientes():
        if request.method == "POST":
            tipo_documento = request.form.get("tipo_documento", "").strip()
            numero_documento = request.form.get("numero_documento", "").strip()
            nombres = request.form.get("nombres", "").strip()
            direccion = request.form.get("direccion", "").strip()
            telefono = request.form.get("telefono", "").strip()
            correo = request.form.get("correo", "").strip()

            if not tipo_documento or not numero_documento or not nombres:
                flash("Completa los campos obligatorios.", "error")
                return redirect(url_for("clientes"))
            if tipo_documento not in TIPOS_DOC_VALIDOS:
                flash("Tipo de documento invalido.", "error")
                return redirect(url_for("clientes"))
            if not re.fullmatch(r"[A-Za-z0-9\-]{5,30}", numero_documento):
                flash("El numero de documento debe tener entre 5 y 30 caracteres (letras, numeros o guion).", "error")
                return redirect(url_for("clientes"))
            if len(nombres) < 3 or len(nombres) > 200:
                flash("El nombre debe tener entre 3 y 200 caracteres.", "error")
                return redirect(url_for("clientes"))
            if correo and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]{2,}", correo):
                flash("El correo electronico no tiene un formato valido.", "error")
                return redirect(url_for("clientes"))
            if telefono and not re.fullmatch(r"[0-9+\-\s]{6,20}", telefono):
                flash("El telefono no tiene un formato valido.", "error")
                return redirect(url_for("clientes"))
            if len(direccion) > 250:
                flash("La direccion es demasiado larga.", "error")
                return redirect(url_for("clientes"))

            conexion = conectar()
            if not conexion:
                flash("No fue posible conectar con MySQL.", "error")
                return redirect(url_for("clientes"))

            cursor = conexion.cursor()
            try:
                cursor.execute("""
                    INSERT INTO clientes
                    (tipo_documento, numero_documento, nombres, direccion, telefono, correo)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (tipo_documento, numero_documento, nombres, direccion, telefono, correo))
                conexion.commit()
                flash("Cliente registrado correctamente.", "success")
            except mysql.connector.Error as error:
                conexion.rollback()
                if getattr(error, "errno", None) == 1062:
                    flash("Ya existe un cliente con ese numero de documento.", "error")
                else:
                    flash(f"Error al registrar el cliente: {error}", "error")
            finally:
                cursor.close()
                conexion.close()
            return redirect(url_for("clientes"))

        conexion = conectar()
        lista = []
        if conexion:
            cur = conexion.cursor(dictionary=True)
            try:
                cur.execute("SELECT * FROM clientes ORDER BY id_cliente DESC")
                lista = cur.fetchall()
            finally:
                cur.close()
                conexion.close()
        return render_template("clientes.html", clientes=lista)
