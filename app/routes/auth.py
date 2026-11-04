# --------------------------------------------------
# LOGIN (credenciales fijas admin/admin) + proteccion de rutas
# --------------------------------------------------
from flask import render_template, request, redirect, url_for, session


# Endpoints que NO exigen sesion (login, estaticos, webhook de Factus Pay y salud)
PUBLIC_ENDPOINTS = {"login", "static", "salud", "webhook_factus_pay", None}


def register(app):

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("user"):
            return redirect(url_for("pos"))
        error = None
        if request.method == "POST":
            usuario = (request.form.get("usuario") or "").strip().lower()
            clave = request.form.get("clave") or ""
            if usuario == "admin" and clave == "admin":
                session["user"] = "admin"
                return redirect(url_for("pos"))
            error = "Credenciales incorrectas."
        return render_template("login.html", error=error,
                               usuario=request.form.get("usuario", ""))

    @app.route("/logout")
    def logout():
        session.pop("user", None)
        return redirect(url_for("login"))

    @app.before_request
    def require_login():
        if request.endpoint in PUBLIC_ENDPOINTS:
            return None
        if not session.get("user"):
            return redirect(url_for("login"))
        return None
