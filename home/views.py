from django.shortcuts import render
from django.contrib.auth import logout
from django.shortcuts import redirect

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


def logout_view(request):
    is_demo = request.session.get('demo_mode', False)
    logout(request)
    if is_demo:
        return redirect('/demo/')
    return redirect('accounts:login')
