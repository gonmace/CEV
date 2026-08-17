"""Inyecta flags de navegación según el rol/capacidades del usuario."""
from django.contrib.auth import get_user_model

from .marca import logo_de
from .models import Role
from .permissions import (
    get_user_empresa, get_user_role, has_capability, is_company_admin,
)


def nav_flags(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    role = get_user_role(user)
    # request.real_user lo cuelga ImpersonationMiddleware cuando el superuser real está
    # impersonando a `user`. Si no existe, `user` ES el real.
    real_user = getattr(request, 'real_user', user)

    # La impersonación está disponible en dev Y en producción, pero SOLO para el superuser
    # real actuando como sí mismo — no para el impersonado (si no, quien es impersonado
    # podría saltar a otra cuenta) NI mientras el superuser ya está impersonando a alguien
    # (para salir se usa el banner rojo de _impersonate.html, no este switcher: si el
    # switcher siguiera visible, un Administrador viendo el menú del superuser impersonado
    # tendría una vía a "Ver la app como…" que se supone que no le corresponde).
    impersonate_available = real_user.is_superuser and real_user is user

    return {
        # Gestión de cuentas: superuser-only (no hay capacidad que la delegue).
        'nav_can_accounts': user.is_superuser,
        # Mi equipo: Administrador de una empresa, acotado a su propia empresa.
        'nav_can_mi_equipo': is_company_admin(user),
        # Módulos: el mismo criterio que aplica ModuleAccessMiddleware, para no ofrecer
        # en el menú un enlace que después responde 403.
        'nav_can_pliegos': has_capability(user, 'pliegos.access'),
        'nav_can_servicios': has_capability(user, 'servicios.access'),
        'nav_is_superuser': user.is_superuser,
        'nav_role': role or '',
        'nav_role_label': dict(Role.choices).get(role, ''),
        # La empresa a la que pertenece, visible siempre en la barra superior. None en las
        # cuentas personales: ahí no se muestra nada (no hay empresa que mostrar).
        'nav_empresa': get_user_empresa(user),
        # Logo de marca (propio del usuario, o si no el de su empresa) para el badge de la
        # barra superior — misma precedencia que se usa al generar los documentos.
        'nav_logo': logo_de(user),
        # Impersonación — ver accounts/middleware.py y accounts/views.impersonate.
        'impersonate_available': impersonate_available,
        'impersonate_active': user if real_user is not user else None,
        'impersonate_real_user': real_user,
        'impersonate_candidates': (
            get_user_model().objects.filter(is_active=True)
            .exclude(pk=real_user.pk).exclude(is_superuser=True)
            .select_related('profile').order_by('email')
            if impersonate_available else None
        ),
    }
