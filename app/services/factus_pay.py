"""Integración Factus Pay (Recaudos / QR Bre-B).

Docs oficiales:
- https://pay-developers.factus.com.co/
- Auth: POST {BASE}/auth {email, password} -> {token}
- Crear: POST {BASE}/v1/collections {reference_code, amount, expiration}
- Ver: GET {BASE}/v1/collections/:referenceCode
- Listar: GET {BASE}/v1/collections
- Webhook: POST a tu URL ?key=LLAVE con {data:{reference_code, amount, status, ...}}

Credenciales sandbox del reto (ver txt de credenciales):
  panel: https://pay-api-sandbox.factus.com.co/
  email: kenner.varilla@campusucc.edu.co
"""
import os
import time
import requests
from requests.exceptions import RequestException
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("FACTUS_PAY_BASE_URL", "https://pay-api-sandbox.factus.com.co").rstrip("/")

# Cache simple en memoria (un solo token activo por usuario según docs)
_token_cache = {"token": None, "ts": 0}


def _credenciales():
    email = os.getenv("FACTUS_PAY_EMAIL", "").strip()
    password = os.getenv("FACTUS_PAY_PASSWORD", "")
    if not email or not password:
        raise Exception(
            "Faltan FACTUS_PAY_EMAIL / FACTUS_PAY_PASSWORD en el .env "
            "(ver 'credenciales reales para usar y cosumir e integrar las apis .txt')"
        )
    return email, password


def obtener_token_pay(force=False):
    """POST /auth -> token. Solo puede existir un token activo por usuario."""
    if not force and _token_cache["token"]:
        return _token_cache["token"]
    email, password = _credenciales()
    url = f"{BASE_URL}/auth"
    try:
        r = requests.post(
            url,
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=20,
        )
        if r.status_code == 401:
            raise Exception("Credenciales Factus Pay inválidas (401). Revisa email/password.")
        r.raise_for_status()
        token = r.json().get("token")
        if not token:
            raise Exception(f"Respuesta auth sin token: {r.text[:300]}")
        _token_cache["token"] = token
        _token_cache["ts"] = time.time()
        return token
    except RequestException as e:
        raise Exception(f"Error de conexión autenticando Factus Pay: {e}")


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def crear_recaudo(reference_code, amount, expiration=86400):
    """POST /v1/collections. Devuelve (status_http, dict_respuesta).

    - reference_code: único por empresa, máx 100 car. Idempotente.
    - amount: pesos COP, 1000 a 12100000, hasta 2 decimales.
    - expiration: segundos de vigencia del QR.
    """
    try:
        token = obtener_token_pay()
    except Exception as e:
        return 500, {"status": "error", "message": str(e), "data": None}

    try:
        monto = float(amount)
    except Exception:
        return 400, {"status": "error", "message": "Monto inválido para Factus Pay.", "data": None}

    if monto < 10000:
        return 400, {
            "status": "error",
            "message": f"Factus Pay exige mínimo $10.000 COP en sandbox (total ${monto:,.2f}). Usa Efectivo o aumenta la venta.",
            "data": None,
        }
    if monto > 12100000:
        return 400, {"status": "error", "message": "Monto supera el máximo de Factus Pay ($12.100.000).", "data": None}

    url = f"{BASE_URL}/v1/collections"
    payload = {
        "reference_code": str(reference_code)[:100],
        "amount": round(monto, 2),
        "expiration": int(expiration or 86400),
    }
    try:
        r = requests.post(url, json=payload, headers=_headers(token), timeout=30)
        try:
            data = r.json()
        except Exception:
            data = {"status": "error", "message": r.text[:500], "data": None}
        # Token revocado / expirado -> reintentar una vez con token fresco
        if r.status_code == 401:
            try:
                token = obtener_token_pay(force=True)
                r = requests.post(url, json=payload, headers=_headers(token), timeout=30)
                try:
                    data = r.json()
                except Exception:
                    data = {"status": "error", "message": r.text[:500], "data": None}
            except Exception as e2:
                return 500, {"status": "error", "message": str(e2), "data": None}
        return r.status_code, data
    except RequestException as e:
        return 500, {"status": "error", "message": f"Error de red Factus Pay: {e}", "data": None}


def consultar_recaudo(reference_code):
    """GET /v1/collections/:referenceCode -> (http, json)."""
    try:
        token = obtener_token_pay()
    except Exception as e:
        return 500, {"status": "error", "message": str(e), "data": None}
    url = f"{BASE_URL}/v1/collections/{reference_code}"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=20)
        try:
            data = r.json()
        except Exception:
            data = {"status": "error", "message": r.text[:500], "data": None}
        if r.status_code == 401:
            token = obtener_token_pay(force=True)
            r = requests.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=20)
            try:
                data = r.json()
            except Exception:
                data = {"status": "error", "message": r.text[:500], "data": None}
        return r.status_code, data
    except RequestException as e:
        return 500, {"status": "error", "message": f"Error de red Factus Pay: {e}", "data": None}


def listar_recaudos(page=1, per_page=20):
    try:
        token = obtener_token_pay()
    except Exception as e:
        return 500, {"status": "error", "message": str(e), "data": None}
    url = f"{BASE_URL}/v1/collections"
    try:
        r = requests.get(
            url,
            params={"page": page, "per_page": per_page},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=20,
        )
        try:
            data = r.json()
        except Exception:
            data = {"status": "error", "message": r.text[:500], "data": None}
        return r.status_code, data
    except RequestException as e:
        return 500, {"status": "error", "message": f"Error de red Factus Pay: {e}", "data": None}
