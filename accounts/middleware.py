"""Middlewares de accounts."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from .permissions import MODULE_ACCESS, has_capability

User = get_user_model()


class ModuleAccessMiddleware:
    """Corta el acceso a los módulos (Proyectos, Servicios) según la capacidad del usuario.

    Se hace por prefijo de URL (`MODULE_ACCESS`) y no con un decorador por vista a propósito:
    son ~50 rutas entre los dos módulos y crecen; una ruta nueva queda protegida sola, sin
    que nadie tenga que acordarse de decorarla. Los anónimos no se tocan acá — de ellos ya se
    encarga `@login_required` mandándolos al login; este middleware solo decide entre 200 y
    403 para alguien que YA está autenticado.

    Va después de AuthenticationMiddleware (necesita request.user) y después de
    DevImpersonationMiddleware, para que al impersonar se apliquen los permisos del
    usuario impersonado y no los del superuser.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            path = request.path
            for prefix, capability in MODULE_ACCESS:
                if path.startswith(prefix) and not has_capability(user, capability):
                    raise PermissionDenied
        return self.get_response(request)


class ImpersonationMiddleware:
    """Permite al SUPERUSER navegar la app siendo realmente otro usuario. Activo también en
    producción — es la forma de reproducir el problema que reporta un cliente sin pedirle la
    contraseña.

    A diferencia de simular un rol, acá se reemplaza `request.user` por el usuario elegido
    (guardado en la sesión como `impersonate_id` por `accounts.views.impersonate`), así que
    la vista ve exactamente lo que ese usuario vería: sus proyectos, su rol real vía
    `Profile`, sus créditos — no hace falta ningún atajo especial en `accounts.permissions`.
    La sesión autenticada sigue siendo la del superuser; el reemplazo es solo en memoria, por
    request. `request.real_user` guarda al superuser real mientras dura la impersonación,
    para el banner y el link de "Salir".

    Seguridad: el gate es `is_superuser` y se comprueba **en cada request**, no solo al
    empezar. Si a alguien le quitan el superuser mientras impersona, deja de impersonar en
    el request siguiente. El único que puede activarla es él mismo (ver views.impersonate).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        real_user = getattr(request, 'user', None)
        if real_user is not None and real_user.is_authenticated and real_user.is_superuser:
            target_id = request.session.get('impersonate_id')
            if target_id:
                target = User.objects.filter(pk=target_id, is_active=True).first()
                if target:
                    request.real_user = real_user
                    request.user = target
        return self.get_response(request)
