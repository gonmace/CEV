"""Fetch de URLs suministradas por el usuario, con protección básica contra SSRF.

`requests.get(url_del_usuario)` sin validar (como hacía `servicios/views.py` en
`extraer_equipo_ajax` y `generar_alcance_ajax`) deja que el servidor alcance
`http://n8n:5678`, `http://postgres:5432`, `http://redis:6379`, `169.254.169.254`
(metadata de proveedores cloud) o cualquier otro host de la red interna: el usuario
autenticado nunca ve la respuesta directamente, pero sí el texto extraído, así que es
un escaneo de puertos/servicios con resultado legible.

`get_seguro()` valida el esquema y resuelve el host ANTES de conectar, rechazando IPs
privadas/loopback/link-local/reservadas, y revalida cada salto si la respuesta es una
redirección (una URL pública puede redirigir a una IP interna). No es infalible —un
atacante con control de DNS puede hacer *rebinding* entre la resolución y la conexión
real de `requests`—, pero cierra el vector directo, que es lo que importa acá.
"""
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests

ESQUEMAS_PERMITIDOS = {'http', 'https'}
MAX_REDIRECCIONES = 5


class URLNoPermitida(Exception):
    """La URL (o una redirección suya) no pasa el filtro SSRF."""


def _resuelve_a_ip_privada(hostname):
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True  # no resuelve: mejor rechazar que dejar pasar
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return True
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return True
    return False


def _validar_url(url):
    partes = urlparse(url)
    if partes.scheme not in ESQUEMAS_PERMITIDOS:
        raise URLNoPermitida(f'Esquema no permitido: {partes.scheme or "(vacío)"}.')
    if not partes.hostname:
        raise URLNoPermitida('La URL no tiene host.')
    if _resuelve_a_ip_privada(partes.hostname):
        raise URLNoPermitida('La URL apunta a una red interna, no permitida.')
    return partes


def get_seguro(url, timeout=15, headers=None, max_bytes=5 * 1024 * 1024):
    """`requests.get` restringido a http(s) público, sin seguir redirecciones a ciegas.

    Lanza `URLNoPermitida` si la URL (o alguna redirección) no pasa el filtro.
    `max_bytes` corta la descarga (evita que una URL "amigo" sirva un archivo enorme
    y sature memoria/CPU del worker).
    """
    actual = url
    for _ in range(MAX_REDIRECCIONES):
        _validar_url(actual)
        resp = requests.get(
            actual, timeout=timeout, headers=headers,
            allow_redirects=False, stream=True,
        )
        if resp.is_redirect or resp.is_permanent_redirect:
            location = resp.headers.get('Location')
            resp.close()
            if not location:
                raise URLNoPermitida('Redirección sin destino.')
            actual = urljoin(actual, location)
            continue

        contenido = resp.raw.read(max_bytes + 1, decode_content=True)
        if len(contenido) > max_bytes:
            resp.close()
            raise URLNoPermitida(f'La respuesta supera el límite de {max_bytes // (1024 * 1024)} MB.')
        resp._content = contenido
        resp._content_consumed = True
        return resp

    raise URLNoPermitida('Demasiadas redirecciones.')
