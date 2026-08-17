"""Sanitización de HTML generado a partir de markdown de usuario.

`markdown.markdown()` no escapa nada: el HTML que produce se vuelca tal cual en las
plantillas con `mark_safe`/`|safe` (especificaciones, servicios, pliegos, el resultado
del demo). Como ese contenido lo escribe el usuario —y en varios flujos se comparte
como `publico=True` con el resto de su empresa, o entre cuentas personales—, un
`<img src=x onerror=...>` guardado en una especificación se ejecuta en el navegador de
cualquiera que la abra. La CSP (`core/settings.py`) es defensa en profundidad, pero hoy
lleva `'unsafe-inline'` en script-src (ver el comentario ahí), así que esta sanitización
es la barrera real.

Basado en `nh3` (bindings de Rust sobre `ammonia`): allowlist de etiquetas/atributos,
igual de estricto que `bleach` pero sin sus dependencias de Python puro.
"""
import nh3

# Lo que puede producir python-markdown con las extensiones que usa el proyecto
# (extra, tables, nl2br, sane_lists, codehilite): texto, tablas, listas, código con
# resaltado por clases CSS, e imágenes (las especificaciones las embeben inline).
ALLOWED_TAGS = {
    'p', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'em', 'b', 'i', 'u', 's', 'del', 'ins', 'sub', 'sup', 'mark', 'small',
    'ul', 'ol', 'li',
    'blockquote', 'pre', 'code', 'span', 'div',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'a', 'img',
}

ALLOWED_ATTRIBUTES = {
    'a': {'href', 'title'},
    'img': {'src', 'alt', 'title', 'width', 'height'},
    'th': {'align'},
    'td': {'align'},
    # codehilite envuelve el código resaltado en <div class="codehilite"><span class="...">:
    # sin permitir `class` acá, `nh3` se comería el atributo y el resaltado quedaría en
    # texto plano sin estilos (no es un riesgo: son nombres de clase generados por la
    # extensión, no por el usuario).
    'div': {'class'},
    'span': {'class'},
    'code': {'class'},
    'pre': {'class'},
}

# Solo http(s) y rutas relativas — bloquea 'javascript:', 'data:text/html', etc. en <a href>.
ALLOWED_URL_SCHEMES = {'http', 'https', 'mailto'}


def sanitizar_html(html):
    """HTML de markdown listo para `mark_safe`/`|safe`. Nunca devuelve `<script>`,
    `on*=`, `javascript:` ni etiquetas fuera de la allowlist."""
    if not html:
        return ''
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel='noopener noreferrer nofollow',
    )
