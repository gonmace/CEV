"""Helpers compartidos para llamar webhooks de n8n y normalizar sus respuestas.

Usado por `pliego_licitacion`, `ubi_web` y `proyectos` (generación de objetivo).
"""
import json
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class N8NError(Exception):
    """Fallo al llamar un webhook de n8n, con mensaje apto para mostrar al usuario."""


def webhook_url(path):
    return f"{settings.N8N_BASE_URL}/webhook/{path}"


def llamar_webhook(url, payload, timeout=120):
    """
    Llama a un webhook de n8n con el payload dado.
    Retorna el JSON parseado de la respuesta.
    Lanza requests.exceptions.RequestException o json.JSONDecodeError si falla.
    """
    headers = {'Content-Type': 'application/json'}
    if settings.N8N_WEBHOOK_TOKEN:
        headers[settings.N8N_WEBHOOK_TOKEN_HEADER] = settings.N8N_WEBHOOK_TOKEN
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=timeout,
    )
    if not response.ok:
        body = response.text[:500]
        raise requests.exceptions.HTTPError(
            f"HTTP {response.status_code} desde {url}: {body}",
            response=response,
        )
    text = response.text.strip()
    if not text:
        return {}
    return response.json()


def llamar_webhook_seguro(url, payload, timeout=120):
    """Como `llamar_webhook`, pero traduce los fallos a `N8NError` con mensaje en español."""
    try:
        return llamar_webhook(url, payload, timeout=timeout)
    except requests.exceptions.Timeout:
        raise N8NError("El servicio de IA tardó demasiado en responder (timeout). Intenta nuevamente.")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else '?'
        logger.error(f"Webhook n8n {url} respondió HTTP {status}: {e}")
        raise N8NError(f"El servicio de IA respondió con un error (HTTP {status}).")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión con webhook n8n {url}: {e}")
        raise N8NError("No se pudo conectar con el servicio de IA.")
    except json.JSONDecodeError:
        raise N8NError("El servicio de IA devolvió una respuesta inválida.")


def desempaquetar(respuesta):
    """n8n envuelve el payload de formas distintas según el workflow: un dict plano,
    `{'output': {...}}`, o una lista de cualquiera de esos dos (`[{...}]`,
    `[{'output': {...}}]`). Normaliza a un dict plano, o `{}` si no reconoce la forma.
    """
    dato = respuesta
    if isinstance(dato, list):
        dato = dato[0] if dato else {}
    if isinstance(dato, dict) and isinstance(dato.get('output'), dict):
        dato = dato['output']
    return dato if isinstance(dato, dict) else {}


_CLAVES_MARKDOWN = ('output', 'pliego', 'contenido', 'markdown', 'text')


def extraer_markdown(respuesta):
    """Extrae el texto markdown de una respuesta de n8n, sea cual sea su envoltura.

    Acepta str directo, dict con alguna de las claves conocidas (recursivo si el
    valor es a su vez dict/list) o lista con cualquiera de los anteriores.
    Retorna str o None si no encuentra texto.
    """
    if respuesta is None:
        return None
    if isinstance(respuesta, str):
        return respuesta if respuesta.strip() else None
    if isinstance(respuesta, list):
        return extraer_markdown(respuesta[0]) if respuesta else None
    if isinstance(respuesta, dict):
        for clave in _CLAVES_MARKDOWN:
            if clave in respuesta:
                texto = extraer_markdown(respuesta[clave])
                if texto:
                    return texto
    return None


def limpiar_markdown_ubicacion(md):
    """Limpieza estructural del markdown devuelto por la IA, sin marcadores literales.

    - Quita un fence envolvente ```markdown ... ```.
    - Corta el preámbulo conversacional: todo lo anterior al primer encabezado.
    - Degrada un único H1 inicial (el documento Word pone su propio título de sección).
    """
    md = (md or '').strip()
    fence = re.match(r'^```[a-zA-Z]*\s*\n(.*)\n```$', md, flags=re.DOTALL)
    if fence:
        md = fence.group(1).strip()
    m = re.search(r'(?m)^#{1,6}\s+\S', md)
    if m:
        if m.start() > 0:
            md = md[m.start():]
    else:
        logger.warning("Respuesta de IA para ubicación sin encabezados markdown; se conserva completa.")
    md = re.sub(r'(?m)\A#\s+.*\n+', '', md, count=1)
    return md.strip()
