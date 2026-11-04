import os
import requests
from requests.exceptions import RequestException
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api-sandbox.factus.com.co"

def obtener_token():
    """
    Obtiene el token de acceso OAuth2 desde Factus con manejo de errores y timeout.
    """
    url = f"{BASE_URL}/oauth/token"
    datos = {
        "grant_type": "password",
        "client_id": os.getenv("FACTUS_CLIENT_ID"),
        "client_secret": os.getenv("FACTUS_CLIENT_SECRET"),
        "username": os.getenv("FACTUS_USERNAME"),
        "password": os.getenv("FACTUS_PASSWORD")
    }

    try:
        respuesta = requests.post(url, data=datos, timeout=20)
        respuesta.raise_for_status()
        return respuesta.json()["access_token"]
    except RequestException as e:
        raise Exception(f"Error de conexión al autenticar con Factus: {str(e)}")


def enviar_factura_a_factus(factura_data):
    """
    Envía una factura a la API de Factus utilizando los datos reales 
    con control de errores de red y timeout.
    """
    try:
        token = obtener_token()
    except Exception as e:
        return 500, {"message": str(e)}

    url = f"{BASE_URL}/v2/bills/validate"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        respuesta = requests.post(url, json=factura_data, headers=headers, timeout=30)
        
        try:
            res_json = respuesta.json()
        except Exception:
            res_json = {"message": respuesta.text}

        return respuesta.status_code, res_json

    except requests.exceptions.ConnectionError as e:
        return 500, {"message": f"Error de conexión con el host remoto (Factus): {str(e)}"}
    except requests.exceptions.Timeout:
        return 500, {"message": "La API de Factus tardó demasiado en responder (Timeout)."}
    except Exception as e:
        return 500, {"message": f"Error inesperado en la petición: {str(e)}"}


def enviar_nota_credito(payload):
    """Envia una nota credito a la API de Factus (POST /v2/credit-notes/validate)."""
    try:
        token = obtener_token()
    except Exception as e:
        return 500, {"message": str(e)}

    url = f"{BASE_URL}/v2/credit-notes/validate"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        respuesta = requests.post(url, json=payload, headers=headers, timeout=40)
        try:
            res_json = respuesta.json()
        except Exception:
            res_json = {"message": respuesta.text}
        return respuesta.status_code, res_json
    except requests.exceptions.ConnectionError as e:
        return 500, {"message": f"Error de conexion con el host remoto (Factus): {str(e)}"}
    except requests.exceptions.Timeout:
        return 500, {"message": "La API de Factus tardo demasiado en responder (Timeout)."}
    except Exception as e:
        return 500, {"message": f"Error inesperado en la peticion: {str(e)}"}


def consultar_rangos():
    """
    Consulta los rangos de numeración activos en Factus.
    """
    try:
        token = obtener_token()
    except Exception as e:
        print(str(e))
        return None

    url = f"{BASE_URL}/v2/numbering-ranges"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    try:
        respuesta = requests.get(url, headers=headers, timeout=20)
        respuesta.raise_for_status()
        return respuesta.json()
    except Exception as e:
        print(f"Error al consultar rangos: {str(e)}")
        return None


def descargar_pdf_factura(factus_id):
    """
    Descarga el archivo PDF desde Factus usando el ID interno del documento.
    """
    try:
        token = obtener_token()
    except Exception as e:
        return 500, {"message": str(e)}

    url = f"{BASE_URL}/v2/bills/download-pdf/{factus_id}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    try:
        respuesta = requests.get(url, headers=headers, timeout=30)
        return respuesta.status_code, respuesta
    except requests.exceptions.Timeout:
        return 500, {"message": "La API de Factus tardó demasiado en responder al descargar el PDF."}
    except Exception as e:
        return 500, {"message": f"Error de red al intentar descargar PDF: {str(e)}"}