import logging
import markdown as md_lib
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from core.sanitize import sanitizar_html
from .models import DemoTrial
from .decorators import demo_login_required, demo_required
from pliego_licitacion.models import EspecificacionTecnica

logger = logging.getLogger(__name__)

_MD_EXTENSIONS = [
    'markdown.extensions.extra',
    'markdown.extensions.tables',
    'markdown.extensions.nl2br',
    'markdown.extensions.sane_lists',
]


def _redirigir_a_paso(spec):
    """Redirige al paso correcto de una demo en curso."""
    if spec.paso <= 1:
        return redirect('demo:flujo_paso1')
    elif spec.paso <= 5:
        return redirect('demo:flujo_paso2', especificacion_id=spec.id)
    else:
        return redirect('demo:flujo_resultado', especificacion_id=spec.id)


@demo_login_required
def landing_view(request):
    """
    Punto de entrada del demo.
    Tres estados: puede intentar / sin cuota / sin cuenta Google.
    """
    no_google = request.GET.get('no_google')
    agotado   = request.GET.get('agotado')

    trial, _ = DemoTrial.objects.get_or_create(usuario=request.user)

    # Retomar demo en curso si existe en sesión
    demo_spec_id = request.session.get('demo_especificacion_id')
    if demo_spec_id:
        try:
            spec = EspecificacionTecnica.objects.get(
                id=demo_spec_id,
                creado_por=request.user,
                eliminado=False,
            )
            if spec.paso < 8:
                return _redirigir_a_paso(spec)
            else:
                del request.session['demo_especificacion_id']
        except EspecificacionTecnica.DoesNotExist:
            del request.session['demo_especificacion_id']

    limite   = trial.max_intentos if trial.max_intentos is not None else getattr(settings, 'DEMO_MAX_TRIALS', 2)
    restantes = max(0, limite - trial.intentos_usados)

    return render(request, 'demo/landing.html', {
        'trial': trial,
        'puede_intentar': trial.puede_intentar(),
        'max_trials': limite,
        'restantes': restantes,
        'no_google': no_google,
        'agotado': agotado,
    })


@demo_required
def iniciar_demo_view(request):
    """POST desde la landing. Registra el intento y redirige al flujo demo."""
    if request.method != 'POST':
        return redirect('demo:landing')

    trial, _ = DemoTrial.objects.get_or_create(usuario=request.user)

    if not trial.puede_intentar():
        return redirect('/demo/?agotado=1')

    trial.registrar_intento()
    request.session['demo_mode'] = True
    request.session.modified = True

    return redirect('demo:flujo_paso1')


# ── Flujo demo ────────────────────────────────────────────────────────────────

@demo_login_required
def flujo_paso1_view(request):
    """Paso 1 del demo: formulario de datos iniciales.

    Exige haber pasado por `iniciar_demo_view` (que registra el intento contra la
    cuota `DemoTrial`): sin esto, cualquier usuario autenticado podía entrar directo
    a esta URL y generar pliegos de demo sin límite.
    """
    if not request.session.get('demo_mode'):
        return redirect('demo:landing')
    return render(request, 'demo/flujo_paso1.html', {
        'es_demo': True,
    })


def _get_demo_spec_or_404(request, especificacion_id):
    """La especificación de la demo EN CURSO de este usuario (no cualquier spec suya:
    el modelo ya no tiene `es_demo`, así que la sesión es la única forma de distinguir
    un pliego de prueba de uno real del mismo usuario)."""
    if str(request.session.get('demo_especificacion_id') or '') != str(especificacion_id):
        raise Http404
    return get_object_or_404(
        EspecificacionTecnica,
        id=especificacion_id,
        creado_por=request.user,
        eliminado=False,
    )


@demo_login_required
def flujo_paso2_view(request, especificacion_id):
    """Paso 2 del demo: selección de parámetros técnicos (4 sub-pasos)."""
    spec = _get_demo_spec_or_404(request, especificacion_id)
    if spec.paso >= 8:
        return redirect('demo:flujo_resultado', especificacion_id=spec.id)
    return render(request, 'demo/flujo_paso2.html', {
        'especificacion': spec,
        'es_demo': True,
    })


@demo_login_required
def flujo_resultado_view(request, especificacion_id):
    """Resultado final del demo, renderizado server-side."""
    spec = _get_demo_spec_or_404(request, especificacion_id)
    resultado_html = sanitizar_html(md_lib.markdown(
        spec.resultado_markdown or '',
        output_format='html',
        extensions=_MD_EXTENSIONS,
    ))
    return render(request, 'demo/flujo_resultado.html', {
        'especificacion': spec,
        'resultado_html': resultado_html,
        'resultado_markdown': spec.resultado_markdown or '',
        'es_demo': True,
    })


# ── Compatibilidad: redirect desde la URL antigua ─────────────────────────────

@demo_login_required
def resultado_demo_view(request, especificacion_id):
    """Redirige a la nueva URL del resultado demo."""
    return redirect('demo:flujo_resultado', especificacion_id=especificacion_id)
