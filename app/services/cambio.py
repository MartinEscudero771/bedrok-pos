# --------------------------------------------------
# SERVICIO: tasa de cambio USD/COP (APIs publicas y gratis)
# 1) https://open.er-api.com/v6/latest/USD  (ExchangeRate-API open, sin llave)
# 2) Fallback: @fawazahmed0/currency-api viajsDelivr CDN
# Cache en memoria de 10 minutos.
# --------------------------------------------------
import time
import requests
from threading import Lock

_cache = {"tasa": None, "fuente": None, "ts": 0, "fecha": None}
_lock = Lock()
TTL_SEGUNDOS = 600  # 10 minutos


def obtener_tasa_usd_cop(force=False):
    """Devuelve dict: {tasa, fuente, fecha} o lanza Exception si ambos fallan."""
    with _lock:
        fresh = not force and _cache["tasa"] and (time.time() - _cache["ts"]) < TTL_SEGUNDOS
        if fresh:
            return {
                "tasa": _cache["tasa"],
                "fuente": _cache["fuente"],
                "fecha": _cache["fecha"],
                "cache": True,
            }
        errores = []
        # 1) open.er-api.com
        try:
            r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=12)
            r.raise_for_status()
            data = r.json()
            tasa = data.get("rates", {}).get("COP")
            if tasa and float(tasa) > 0:
                _guardar(float(tasa), "ExchangeRate-API (open.er-api.com)",
                         data.get("time_last_update_utc", ""))
                return _salida()
        except Exception as e:
            errores.append(f"er-api: {e}")
        # 2) fallback jsdelivr currency-api
        try:
            r = requests.get(
                "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
                timeout=12,
            )
            r.raise_for_status()
            data = r.json()
            tasa = (data.get("usd") or {}).get("cop")
            if tasa and float(tasa) > 0:
                _guardar(float(tasa), "currency-api (jsDelivr)", data.get("date", ""))
                return _salida()
        except Exception as e:
            errores.append(f"jsdelivr: {e}")
        if _cache["tasa"]:
            # respuesta de ultimo recurso: ultima tasa cacheada aunque expire
            return _salida()
        raise Exception("No fue posible obtener la tasa USD/COP: " + " | ".join(errores))


def _guardar(tasa, fuente, fecha):
    _cache["tasa"] = round(float(tasa), 4)
    _cache["fuente"] = fuente
    _cache["fecha"] = fecha
    _cache["ts"] = time.time()


def _salida():
    return {
        "tasa": _cache["tasa"],
        "fuente": _cache["fuente"],
        "fecha": _cache["fecha"],
        "cache": time.time() - _cache["ts"] < TTL_SEGUNDOS,
    }
