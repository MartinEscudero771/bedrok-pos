"""Fábrica de la aplicación Flask — Bedrok POS + Factus + Factus Pay."""
import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv()


def _pkg_path(*parts):
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", *parts))


def create_app():
    app = Flask(
        __name__,
        template_folder=_pkg_path("templates"),
        static_folder=_pkg_path("static"),
    )
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "clave-temporal-bedrok")

    from .utils import fmt_cop, fmt_num, fmt_moneda
    app.jinja_env.filters["cop"] = fmt_cop
    app.jinja_env.filters["num"] = fmt_num
    app.jinja_env.filters["usd"] = fmt_moneda

    from .database import init_db
    try:
        init_db()
    except Exception as e:
        print("init_db:", e)

    from .routes.auth import register as register_auth
    from .routes.pos import register as register_pos
    from .routes.clientes import register as register_clientes
    from .routes.productos import register as register_productos
    from .routes.facturas import register as register_facturas
    from .routes.pagos import register as register_pagos
    from .routes.pedidos import register as register_pedidos

    register_auth(app)
    register_pos(app)
    register_clientes(app)
    register_productos(app)
    register_facturas(app)
    register_pagos(app)
    register_pedidos(app)

    return app


def run():
    create_app().run(debug=True, port=5000)
