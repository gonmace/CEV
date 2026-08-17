import os

from django.conf import settings


def site_logo(request):
    return {
        'site_logo_url': getattr(settings, 'SITE_LOGO_URL', ''),
        'css_version': _css_version(),
    }


def _css_version():
    """Marca de versión del CSS compilado, para colgarla del <link> como ?v=…

    Sin esto, el navegador se queda con el styles.css cacheado y los cambios de Tailwind
    no se ven hasta un hard-refresh — que es exactamente el síntoma de "DaisyUI no
    renderiza". En DEBUG se usa el mtime del archivo (cambia en cada recompilación del
    watch); en producción basta con calcularlo una vez por proceso.
    """
    if not settings.DEBUG and _css_version.cached:
        return _css_version.cached
    ruta = os.path.join(settings.BASE_DIR, 'static', 'css', 'dist', 'styles.css')
    try:
        version = str(int(os.path.getmtime(ruta)))
    except OSError:
        version = ''
    _css_version.cached = version
    return version


_css_version.cached = ''
