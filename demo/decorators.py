from functools import wraps
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


GOOGLE_LOGIN_URL = '/accounts/google/login/?next=/demo/'
DEV_DEMO_USERNAME = 'demo_dev'


def ensure_dev_demo_user(request):
    """
    En desarrollo permite usar el demo sin OAuth externo, manteniendo un User real
    para las relaciones y filtros por propietario del flujo.
    """
    if not settings.DEBUG or request.user.is_authenticated:
        return request.user

    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=DEV_DEMO_USERNAME,
        defaults={
            'email': 'demo@localhost',
            'first_name': 'Demo',
            'last_name': 'Local',
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return user


def demo_login_required(view_func):
    """Login Google en producción; usuario local automático en desarrollo."""
    protected_view = login_required(login_url=GOOGLE_LOGIN_URL)(view_func)

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if settings.DEBUG:
            ensure_dev_demo_user(request)
            return view_func(request, *args, **kwargs)
        return protected_view(request, *args, **kwargs)

    return _wrapped


def demo_required(view_func):
    """
    Exige usuario autenticado con cuenta Google vinculada.
    - Sin autenticación → redirige a /accounts/google/login/?next=/demo/
    - Sin cuenta Google → redirige a /demo/?no_google=1
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if settings.DEBUG:
            ensure_dev_demo_user(request)
            return view_func(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return redirect(GOOGLE_LOGIN_URL)
        if not request.user.socialaccount_set.filter(provider='google').exists():
            return redirect('/demo/?no_google=1')
        return view_func(request, *args, **kwargs)
    return _wrapped
