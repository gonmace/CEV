"""Capacidades del sistema y helpers de autorización.

Las capacidades NO se hardcodean en las vistas. Se resuelven en dos niveles:

1. El rol del usuario fija el default, en la matriz rol × capacidad que el superuser
   edita en el tablero de toggles (`RolePermission`).
2. Cualquier cuenta puede tener ese default pisado capacidad por capacidad con un
   override individual (`UserPermission`), editable desde su ficha (accounts:user_edit).
   Aplica a todos los roles: el override siempre gana sobre el default del rol.

Aquí se define el catálogo de capacidades, los valores por defecto que siembra la data
migration, y los helpers que las consultan.
"""
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import Role, RolePermission, UserPermission

# (clave, etiqueta legible) — el tablero de toggles muestra todas estas filas.
CAPABILITIES = [
    ('pliegos.access', 'Módulo Proyectos'),
    ('servicios.access', 'Módulo Servicios'),
    # Lo único que distingue al Administrador del Usuario: sin esto solo se ven los
    # datos propios (filtrado por creado_por), con esto se ven también los privados de
    # los compañeros de SU empresa. La vista global de verdad es solo del superuser.
    ('data.view_all', 'Ver los datos de todos los usuarios de su empresa'),
]

CAPABILITY_KEYS = [key for key, _ in CAPABILITIES]

# Los módulos con su etiqueta corta, para las columnas de la tabla de cuentas
# (accounts:access_admin). Es el subconjunto de CAPABILITIES que se puede togglear ahí.
MODULES = [
    ('pliegos.access', 'Proyectos'),
    ('servicios.access', 'Servicios'),
]

MODULE_KEYS = [key for key, _ in MODULES]

# Prefijo de URL → capacidad que exige. Lo aplica ModuleAccessMiddleware, así que una
# ruta nueva dentro de un módulo ya existente queda protegida sin tocar la vista.
#
# El módulo "Proyectos" son las tres apps del flujo, no solo /pliego/: se entra por
# /proyectos/ (es a donde apunta la tarjeta del landing), las ubicaciones cuelgan de un
# proyecto, y /pliego/ es el generador. Dar acceso a una sin las otras deja el flujo roto.
MODULE_ACCESS = (
    ('/proyectos/', 'pliegos.access'),
    ('/pliego/', 'pliegos.access'),
    ('/ubicaciones/', 'pliegos.access'),
    ('/servicios/', 'servicios.access'),
)

# Rutas de administración: solo el superuser entra. Se usan para no mandar a un usuario
# impersonado a una página que le daría 403 nada más empezar (ver views.impersonate).
SUPERUSER_ONLY = (
    '/acceso/admin/',
    '/acceso/roles/',
    '/acceso/correo/',
    '/acceso/cuenta/',
)

# Defaults sembrados por la migración (editables luego en el tablero por el superuser).
# El Usuario entra a ambos módulos: es el comportamiento que la app tenía antes de que
# los módulos se pudieran restringir, así que nadie pierde acceso al migrar.
DEFAULT_ROLE_CAPS = {
    Role.USUARIO: {'pliegos.access', 'servicios.access'},
    Role.ADMINISTRADOR: {'pliegos.access', 'servicios.access', 'data.view_all'},
}


def get_user_role(user):
    """Rol del usuario (Usuario si no tiene Profile aún)."""
    if not user or not user.is_authenticated:
        return None
    profile = getattr(user, 'profile', None)
    return profile.role if profile else Role.USUARIO


def get_user_empresa(user):
    """La empresa del usuario, o None si es una cuenta personal (o anónima).

    Es la distinción entre los dos tipos de cuenta: con empresa, comparte bolsa de
    créditos y cupo con su equipo; sin ella, sus créditos son suyos y no tiene equipo."""
    if not user or not user.is_authenticated:
        return None
    profile = getattr(user, 'profile', None)
    return profile.empresa if profile else None


def is_company_admin(user):
    """True si `user` administra el equipo de SU PROPIA empresa (accounts:mi_equipo).

    Distinto de `data.view_all`: esa capacidad es global (ve los datos de todo el
    mundo), esto es acotado a su empresa (agregar miembros, promoverlos, fijarles
    tope). Una cuenta personal (sin empresa) nunca es company admin, aunque tenga
    el rol Administrador — no hay equipo que administrar."""
    return (
        bool(user) and user.is_authenticated
        and get_user_role(user) == Role.ADMINISTRADOR
        and get_user_empresa(user) is not None
    )


def _load_capability_set(user):
    """Todas las capacidades habilitadas para `user` en 2 queries (overrides + matriz de
    rol), resolviendo override individual gana sobre el default del rol."""
    role = get_user_role(user)
    if role is None:
        return frozenset()
    overrides = dict(UserPermission.objects.filter(user=user).values_list('capability', 'enabled'))
    role_caps = set(RolePermission.objects.filter(role=role, enabled=True).values_list('capability', flat=True))
    enabled = set()
    for key in CAPABILITY_KEYS:
        if key in overrides:
            if overrides[key]:
                enabled.add(key)
        elif key in role_caps:
            enabled.add(key)
    return frozenset(enabled)


def has_capability(user, capability):
    """True si el usuario tiene la capacidad. El superuser saltea todos los checks.

    Si el usuario tiene un override individual (UserPermission) para esta capacidad,
    gana sobre el default de su rol; si no hay fila, se usa el default del rol.

    El resultado se memoiza en el propio objeto `user` (2 queries la primera vez que se
    llama en el request, cero las siguientes) — `request.user` es la misma instancia
    durante todo el request, así que el cache no sobrevive entre requests."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if '_capability_set' not in user.__dict__:
        user.__dict__['_capability_set'] = _load_capability_set(user)
    return capability in user.__dict__['_capability_set']


def users_with_capability(capability):
    """Usuarios activos que tienen la capacidad habilitada. Replica la lógica de
    has_capability (override individual gana sobre el default del rol) como queryset.
    Excluye a los superusers puros a propósito: su bypass es administrativo, no
    significa que quieran recibir cada notificación operativa."""
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    User = get_user_model()
    roles = RolePermission.objects.filter(
        capability=capability, enabled=True).values_list('role', flat=True)
    override_on = UserPermission.objects.filter(
        capability=capability, enabled=True).values_list('user_id', flat=True)
    override_off = UserPermission.objects.filter(
        capability=capability, enabled=False).values_list('user_id', flat=True)
    return User.objects.filter(is_active=True).filter(
        Q(pk__in=override_on) | (Q(profile__role__in=roles) & ~Q(pk__in=override_off))
    ).distinct()


def anotar_modulos(users):
    """Cuelga `user.modulos` en cada usuario de la lista: el estado EFECTIVO de cada módulo,
    listo para pintar los toggles de la tabla de cuentas.

    Resuelve toda la página en 2 queries (matriz de roles + overrides de esos usuarios), en vez
    de llamar a has_capability() por usuario y columna, que sería un N+1 por celda.

    Cada entrada: {key, label, enabled, is_override, locked}. `locked` marca al superuser, que
    tiene todo por bypass y cuyo toggle no se puede cambiar (ver has_capability)."""
    users = list(users)
    if not users:
        return users

    role_matrix = {
        (rp.role, rp.capability): rp.enabled
        for rp in RolePermission.objects.filter(capability__in=MODULE_KEYS)
    }
    overrides = {
        (up.user_id, up.capability): up.enabled
        for up in UserPermission.objects.filter(
            user__in=users, capability__in=MODULE_KEYS,
        )
    }

    for user in users:
        role = get_user_role(user)
        user.modulos = []
        for key, label in MODULES:
            is_override = (user.pk, key) in overrides
            if user.is_superuser:
                enabled = True
            elif is_override:
                enabled = overrides[(user.pk, key)]
            else:
                enabled = role_matrix.get((role, key), False)
            user.modulos.append({
                'key': key,
                'label': label,
                'enabled': enabled,
                'is_override': is_override and not user.is_superuser,
                'locked': user.is_superuser,
            })
    return users


def puede_acceder_a(user, path):
    """¿`user` puede abrir esta URL sin comerse un 403?

    Comprueba lo mismo que los gates de la app: las rutas de administración
    (`SUPERUSER_ONLY`) y el acceso a módulos (`MODULE_ACCESS`, lo que aplica
    ModuleAccessMiddleware).

    Se usa al impersonar: el superuser suele arrancar la impersonación desde una página que
    la otra persona no puede ver (la de Cuentas, o un módulo que no tiene habilitado), y
    devolverla ahí la recibiría con un 403. No pretende adivinar permisos de objeto (si un
    proyecto concreto es suyo o no) — solo evita el 403 seguro.
    """
    if not path or not path.startswith('/'):
        return False
    if any(path.startswith(p) for p in SUPERUSER_ONLY):
        return bool(user and user.is_authenticated and user.is_superuser)
    for prefijo, capacidad in MODULE_ACCESS:
        if path.startswith(prefijo):
            return has_capability(user, capacidad)
    return True


def puede_ver_todo(user):
    """True si el usuario ve TODOS los datos de la plataforma, sin límite de empresa —
    reservado al superuser. El Administrador de una empresa NO entra acá: ve todo, pero
    acotado a la suya (lo resuelven aparte filtrar_visibles/puede_ver/puede_editar)."""
    return bool(user and user.is_authenticated and user.is_superuser)


def _resolver_campo(obj, ruta):
    """Sigue una ruta tipo 'proyecto__empresa' con getattr, tolerando None en el camino."""
    for parte in ruta.split('__'):
        if obj is None:
            return None
        obj = getattr(obj, parte, None)
    return obj


def filtrar_visibles(qs, user, campo='creado_por', campo_publico='publico', campo_empresa='empresa'):
    """Restringe un queryset a lo visible por `user` — cada empresa es un compartimento
    estanco, como si fuera una aplicación separada: nunca ve datos de otra empresa ni de
    cuentas personales, y viceversa.

    - Superuser: sin filtro (rol de plataforma, no de una empresa).
    - Administrador (data.view_all) CON empresa: todo lo de SU empresa (propio y ajeno).
    - Administrador SIN empresa (cuenta personal): solo lo suyo, como un Usuario.
    - Resto: lo propio, más lo público dentro de su mismo alcance (su empresa, o entre
      cuentas personales si no tiene empresa) — `publico=True` de OTRA empresa nunca
      entra. `campo_publico=None` para modelos sin ese flag (p. ej. los borradores de
      EspecificacionTecnica): ahí no hay "público", solo lo propio (o lo de la empresa,
      si corresponde por data.view_all)."""
    if puede_ver_todo(user):
        return qs
    empresa = get_user_empresa(user)
    if has_capability(user, 'data.view_all'):
        if empresa is not None:
            return qs.filter(**{campo_empresa: empresa})
        return qs.filter(**{campo: user})
    if campo_publico:
        alcance = {campo_empresa: empresa} if empresa is not None else {f'{campo_empresa}__isnull': True}
        return qs.filter(Q(**{campo: user}) | (Q(**{campo_publico: True}) & Q(**alcance)))
    return qs.filter(**{campo: user})


def puede_ver(user, obj, campo='creado_por', campo_publico='publico', campo_empresa='empresa'):
    """True si `user` puede VER el objeto, respetando el aislamiento por empresa: lo
    público de otra empresa (o de una cuenta personal ajena) no cuenta como visible."""
    if not user or not user.is_authenticated:
        return False
    if puede_ver_todo(user):
        return True
    empresa = get_user_empresa(user)
    obj_empresa = _resolver_campo(obj, campo_empresa)
    if has_capability(user, 'data.view_all') and empresa is not None and obj_empresa == empresa:
        return True
    if campo_publico and getattr(obj, campo_publico, False):
        return obj_empresa == empresa
    return getattr(obj, campo, None) == user


def puede_editar(user, obj, campo='creado_por', campo_empresa='empresa'):
    """True si `user` puede MODIFICAR el objeto: lo creó, es superuser, o es
    Administrador (data.view_all) de la MISMA empresa dueña del objeto.

    Ojo con la diferencia respecto de `puede_ver`: que algo sea público lo hace legible
    para su alcance, pero NO editable — eso sigue siendo del dueño o de su Administrador."""
    if not user or not user.is_authenticated:
        return False
    if puede_ver_todo(user):
        return True
    if getattr(obj, campo, None) == user:
        return True
    empresa = get_user_empresa(user)
    if has_capability(user, 'data.view_all') and empresa is not None:
        return _resolver_campo(obj, campo_empresa) == empresa
    return False


def require_capability(capability):
    """Decorador para vistas: 403 si el usuario no tiene la capacidad."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not has_capability(request.user, capability):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
