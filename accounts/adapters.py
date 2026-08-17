"""Adapters de django-allauth: cierran el registro público.

El alta con email+contraseña tiene su propio flujo, ya construido y con su allow-list
(`accounts.views.request_access` → link de activación → `activate`). El formulario
genérico de allauth (`/accounts/signup/`) no debía estar disponible en paralelo, pero
sin un `ACCOUNT_ADAPTER` propio, `is_open_for_signup()` cae en el default de allauth
(`True`): cualquiera podía registrarse ahí, saltándose `accounts.access.is_email_allowed`
y todo el sistema de roles/empresa/créditos. Ídem el login social (Google): sin
`SOCIALACCOUNT_ADAPTER`, cualquier cuenta de Google entraba y quedaba con el rol
`Usuario` por defecto sin haber sido invitada nunca.
"""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .access import is_email_allowed, resolve_default_role, resolve_empresa
from .models import Profile


class AccountAdapter(DefaultAccountAdapter):
    """Cierra `/accounts/signup/` (email + contraseña): esa alta pasa por
    `accounts.views.request_access` + el link de activación, no por acá."""

    def is_open_for_signup(self, request, *args, **kwargs):
        return False


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Login con Google: solo para correos habilitados (misma allow-list que el alta
    por email — dominio de una Empresa con cupo, o `AllowedEmail` individual)."""

    def is_open_for_signup(self, request, sociallogin):
        email = (sociallogin.user.email or '').strip().lower()
        return bool(email) and is_email_allowed(email)

    def save_user(self, request, sociallogin, form=None):
        """Crea el `Profile` (rol + empresa) igual que `accounts.views.activate` para
        el alta por email: sin esto, el usuario entraba sin Profile y `get_user_role`
        caía al fallback `Usuario` sin quedar nunca vinculado a su empresa."""
        user = super().save_user(request, sociallogin, form)
        email = (user.email or '').strip().lower()
        empresa = resolve_empresa(email)
        if empresa and not empresa.hay_cupo:
            # El cupo se llenó entre `is_open_for_signup` y este guardado (carrera
            # improbable pero posible): no dejar al usuario colgado de una empresa llena.
            empresa = None
        Profile.objects.get_or_create(
            user=user,
            defaults={'role': resolve_default_role(email), 'empresa': empresa},
        )
        return user
