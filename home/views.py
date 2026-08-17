from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from accounts.creditos import consumido_por, disponible


def index(request):
    # Home pública: la ve cualquiera, logueado o no. Los créditos son un dato de la
    # cuenta, así que solo tienen sentido si hay sesión — sin login_required acá, quien
    # entra sin sesión ve las cards igual (para eso están) y recién se le pide login al
    # tratar de entrar a un módulo (@login_required en proyectos/servicios).
    context = {}
    if request.user.is_authenticated:
        # `disponible` es lo que ESTA persona puede gastar (su tope individual si lo
        # tiene, si no la bolsa compartida); `usados` es cuánto lleva consumido ella —
        # dato individual, útil sobre todo en una empresa, donde el saldo baja por el
        # uso de todo el equipo.
        context['creditos_pliegos'] = disponible(request.user, 'pliegos.access')
        context['creditos_servicios'] = disponible(request.user, 'servicios.access')
        context['usados_pliegos'] = consumido_por(request.user, 'pliegos.access')
        context['usados_servicios'] = consumido_por(request.user, 'servicios.access')
    return render(request, 'home/index.html', context)


@require_POST
def logout_view(request):
    # Todos los templates ya lo llaman por un <form method="post">; exigirlo acá cierra
    # el logout-CSRF (forzar la sesión de otro con un <img src="/logout/">).
    is_demo = request.session.get('demo_mode', False)
    logout(request)
    if is_demo:
        return redirect('/demo/')
    return redirect('accounts:login')


def healthz(request):
    """Sondeo de salud para el healthcheck de Docker/nginx: sin auth, sin BD, sin
    caché — solo confirma que el proceso Django responde. Deliberadamente no verifica
    Postgres/Redis: un healthcheck que depende de ellos puede tumbar el contenedor por
    un problema de infraestructura ajeno a la app."""
    return HttpResponse('ok', content_type='text/plain')
