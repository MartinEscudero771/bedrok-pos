# --------------------------------------------------
# INICIO / POS / CREAR FACTURA (vista)
# --------------------------------------------------
from mysql.connector import Error as MySQLError
from flask import render_template

from ..database import conectar


def register(app):

    @app.route("/")
    def inicio():
        from flask import redirect, url_for
        return redirect(url_for("pos"))

    @app.route("/pos")
    def pos():
        conexion = conectar()
        if not conexion:
            return "No fue posible conectar con MySQL. Revisa tu .env", 500
        cur = conexion.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM clientes WHERE activo=TRUE ORDER BY nombres")
            clientes = cur.fetchall()
            cur.execute("SELECT * FROM productos WHERE activo=TRUE ORDER BY nombre")
            productos = cur.fetchall()
        finally:
            cur.close()
            conexion.close()
        return render_template("pos.html", clientes=clientes, productos=productos)

    @app.route("/crear-factura")
    def crear_factura():
        conexion = conectar()
        if not conexion:
            return "No fue posible conectar con MySQL.", 500
        cur = conexion.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM clientes WHERE activo=TRUE ORDER BY nombres")
            clientes = cur.fetchall()
            cur.execute(
                "SELECT * FROM productos WHERE activo=TRUE AND stock>0 ORDER BY nombre"
            )
            productos = cur.fetchall()
        finally:
            cur.close()
            conexion.close()
        return render_template("crear_factura.html", clientes=clientes, productos=productos)
