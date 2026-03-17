import requests
import json
import markdown
import logging
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .forms import EspecificacionTecnicaForm
from .models import EspecificacionTecnica

logger = logging.getLogger(__name__)


def llamar_webhook(url, payload, timeout=120):
    """
    Llama a un webhook de n8n con el payload dado.
    Retorna el JSON parseado de la respuesta.
    Lanza requests.exceptions.RequestException o json.JSONDecodeError si falla.
    """
    response = requests.post(
        url,
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=timeout,
    )
    if not response.ok:
        body = response.text[:500]
        raise requests.exceptions.HTTPError(
            f"HTTP {response.status_code} desde {url}: {body}",
            response=response,
        )
    text = response.text.strip()
    if not text:
        return {}
    return response.json()


N8N_WEBHOOK_COHERENCIA_URL = 'https://n8n.magoreal.com/webhook/coherencia'
N8N_WEBHOOK_PARAMETROS_URL = 'https://n8n.magoreal.com/webhook/parametros'
N8N_WEBHOOK_TITULO_URL = 'https://n8n.magoreal.com/webhook/titulo'
N8N_WEBHOOK_ADICIONALES_URL = 'https://n8n.magoreal.com/webhook/adicionales'
N8N_WEBHOOK_FINAL_URL = 'https://n8n.magoreal.com/webhook/final'


# ── Vista principal ────────────────────────────────────────────────────────────

@login_required
def pasos_view(request):
    """
    Vista principal con sistema de pasos
    """
    try:
        pasos = [
            {"numero": 1, "nombre": "Parámetros"},
            {"numero": 2, "nombre": "Título"},
            {"numero": 3, "nombre": "Adicionales"},
            {"numero": 4, "nombre": "Actividades"},
            {"numero": 5, "nombre": "Resultado"},
        ]
        paso_actual = int(request.GET.get('paso', 1))

        # Guardar proyecto_id en la sesión si viene como parámetro GET
        proyecto_id = request.GET.get('proyecto_id')
        if proyecto_id:
            try:
                proyecto_id = int(proyecto_id)
                from proyectos.models import Proyecto
                proyecto = Proyecto.objects.get(id=proyecto_id, activo=True)
                if proyecto.creado_por == request.user or proyecto.publico:
                    request.session['pliego_proyecto_id'] = proyecto_id
                    request.session.modified = True
                    logger.info(f"pasos_view - Proyecto ID {proyecto_id} guardado en sesión para paso {paso_actual}")
                else:
                    logger.warning(f"pasos_view - Usuario no tiene acceso al proyecto {proyecto_id}")
            except (ValueError, Proyecto.DoesNotExist) as e:
                logger.warning(f"pasos_view - Proyecto no válido o no encontrado: {str(e)}")
            except Exception as e:
                logger.error(f"pasos_view - Error al procesar proyecto_id: {str(e)}", exc_info=True)

        proyecto_id_sesion = request.session.get('pliego_proyecto_id')
        if proyecto_id_sesion:
            logger.info(f"pasos_view - Proyecto ID {proyecto_id_sesion} encontrado en sesión para paso {paso_actual}")
            request.session.modified = True
        else:
            logger.warning(f"pasos_view - ⚠️ No hay proyecto_id en la sesión para paso {paso_actual}")

        if paso_actual != 5:
            request.session.pop('pliego_paso1_data', None)
            request.session.pop('pliego_respuesta_api', None)
            request.session.pop('pliego_respuesta_completa', None)
            request.session.pop('pliego_actividades_adicionales', None)

        datos_paso1 = {}
        respuesta_api = {}
        respuesta_completa = {}
        actividades_adicionales = {}

        if paso_actual == 1:
            template_name = 'pliego_licitacion/paso1_datos_iniciales.html'
        elif paso_actual == 5:
            template_name = 'pliego_licitacion/paso8_resultado.html'
        else:
            template_name = 'pliego_licitacion/pasos.html'

        # Especificaciones incompletas del proyecto actual
        borradores = []
        pid = proyecto_id if isinstance(proyecto_id, int) else proyecto_id_sesion
        if pid and paso_actual == 1:
            try:
                from proyectos.models import Proyecto
                from django.db.models import Q
                proy = Proyecto.objects.filter(id=pid).first()
                if proy:
                    borradores = list(
                        EspecificacionTecnica.objects.filter(
                            Q(proyecto=proy) | Q(proyecto__isnull=True, creado_por=request.user),
                            eliminado=False,
                            paso__gte=2,
                            paso__lt=8,
                        ).order_by('-fecha_actualizacion')
                    )
                    # Vincular retroactivamente los sin proyecto al proyecto actual
                    ids_sin_proyecto = [b.id for b in borradores if b.proyecto_id is None]
                    if ids_sin_proyecto:
                        EspecificacionTecnica.objects.filter(id__in=ids_sin_proyecto).update(proyecto=proy)
                        for b in borradores:
                            if b.proyecto_id is None:
                                b.proyecto = proy
            except Exception as e:
                logger.error(f"pasos_view - Error al obtener borradores: {e}", exc_info=True)

        # Etiqueta del SIGUIENTE paso a completar (paso+1)
        _NEXT_LABELS = {
            2: (3, 'Ejecución'),
            3: (4, 'Normas'),
            4: (5, 'Criterios'),
            5: (6, 'Título'),
            6: (7, 'Actividades'),
            7: (8, 'Generar resultado'),
        }
        borradores_ctx = []
        for b in borradores:
            next_num, next_label = _NEXT_LABELS.get(b.paso, (b.paso + 1, 'Continuar'))
            borradores_ctx.append({
                'obj': b,
                'resume_paso': next_num,
                'resume_label': next_label,
            })

        # Nombre del proyecto para el header
        proyecto_nombre_ctx = ''
        proyecto_obj = None
        if pid:
            try:
                from proyectos.models import Proyecto
                proyecto_obj = Proyecto.objects.filter(id=pid).first()
                if proyecto_obj:
                    proyecto_nombre_ctx = proyecto_obj.nombre
            except Exception:
                pass

        return render(request, template_name, {
            'pasos': pasos,
            'paso_actual': paso_actual,
            'datos_paso1': datos_paso1,
            'respuesta_api': respuesta_api,
            'respuesta_completa': respuesta_completa,
            'actividades_adicionales': actividades_adicionales,
            'form': EspecificacionTecnicaForm(),
            'borradores': borradores_ctx,
            'proyecto_id': pid,
            'proyecto_nombre': proyecto_nombre_ctx,
            'proyecto': proyecto_obj,
        })
    except Exception as e:
        logger.error(f"Error inesperado en pasos_view: {str(e)}", exc_info=True)
        from django.http import HttpResponseServerError
        return HttpResponseServerError('Error interno del servidor. Por favor, contacte al administrador.')


# ── Paso 1: Datos iniciales ────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def coherencia_view(request):
    """
    Paso 1: Guarda la especificación en BD y llama al webhook de coherencia.
    Si coherente=True, el frontend llama a paso1/parametros/.
    """
    try:
        data = json.loads(request.body)
        titulo = data.get('titulo', '').strip()
        descripcion = data.get('descripcion', '').strip()
        tipo_servicio = data.get('tipo_servicio', '').strip()
        unidad_medida = data.get('unidad_medida', '').strip()

        if not titulo or not descripcion or not tipo_servicio or not unidad_medida:
            return JsonResponse({
                'success': False,
                'error': 'Título, descripción, tipo de servicio y unidad de medida son requeridos'
            }, status=400)

        if len(unidad_medida) > 10:
            unidad_medida = unidad_medida[:10]

        # Guardar en BD
        try:
            _proyecto = None
            _proyecto_id = request.session.get('pliego_proyecto_id')
            if _proyecto_id:
                try:
                    from proyectos.models import Proyecto
                    _proyecto = Proyecto.objects.filter(id=_proyecto_id, activo=True).first()
                except Exception:
                    pass
            especificacion = EspecificacionTecnica.objects.create(
                titulo=titulo,
                descripcion=descripcion,
                tipo_servicio=tipo_servicio,
                unidad_medida=unidad_medida,
                creado_por=request.user,
                proyecto=_proyecto,
                paso=1,
            )
            logger.info(f"EspecificacionTecnica guardada con ID: {especificacion.id}")
        except Exception as e:
            logger.error(f"Error al guardar EspecificacionTecnica: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'Error al guardar la especificación técnica. Por favor, intente nuevamente.'
            }, status=500)

        payload = {
            'id': especificacion.id,
            'titulo': titulo,
            'descripcion': descripcion,
            'tipo_servicio': tipo_servicio,
            'unidad_medida': unidad_medida
        }

        # Llamar webhook de coherencia
        response_data = llamar_webhook(N8N_WEBHOOK_COHERENCIA_URL, payload)

        # Normalizar respuesta (puede venir como lista o dict)
        item = response_data[0] if isinstance(response_data, list) and response_data else response_data
        output = item.get('output', item) if isinstance(item, dict) else {}

        # Incoherente: { "coherente": false, "razon": "..." }
        if isinstance(output, dict) and output.get('coherente') is False:
            logger.info(f"Incoherencia detectada para EspecificacionTecnica {especificacion.id}: {output.get('razon', '')}")
            return JsonResponse({
                'success': True,
                'coherente': False,
                'razon': output.get('razon', ''),
            })

        # Coherente: guardar clasificación directamente sin envolver en id
        if isinstance(output, dict) and 'sistema_constructivo' in output:
            clasificacion = {k: v for k, v in output.items() if k != 'id'}
            especificacion.clasificacion = clasificacion
            especificacion.save(update_fields=['clasificacion'])
            logger.info(f"Clasificación guardada para EspecificacionTecnica {especificacion.id}: {clasificacion}")

        return JsonResponse({
            'success': True,
            'coherente': True,
            'especificacion_id': especificacion.id,
        })

    except requests.exceptions.Timeout:
        logger.error("Timeout en enviar_especificacion_view")
        return JsonResponse({
            'success': False,
            'error': 'La solicitud tardó demasiado tiempo. Por favor, intente nuevamente.'
        }, status=408)
    except requests.exceptions.RequestException as e:
        print(f"!!! RequestException: {type(e).__name__}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"!!! HTTP status: {e.response.status_code}")
            print(f"!!! Response body: {e.response.text[:500]}")
        logger.error(f"RequestException en enviar_especificacion_view: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Error al comunicarse con la API. Por favor, intente nuevamente más tarde.'
        }, status=500)
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError en enviar_especificacion_view: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado en enviar_especificacion_view: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor. Por favor, contacte al administrador o intente nuevamente más tarde.'
        }, status=500)


# ── Pasos 1-1 a 1-4: Sub-pasos de clasificación ───────────────────────────────
# El frontend los ejecuta en secuencia tras recibir coherente=True.
# Todos comparten el mismo payload base (id, titulo, descripcion, tipo_servicio,
# unidad_medida, clasificacion) y retornan {success, especificacion_id, response_data}.

def _payload_base(especificacion):
    return {
        'id': especificacion.id,
        'titulo': especificacion.titulo,
        'descripcion': especificacion.descripcion,
        'tipo_servicio': especificacion.tipo_servicio,
        'unidad_medida': especificacion.unidad_medida,
        'clasificacion': especificacion.clasificacion or {},
    }


def _sub_paso_view(request, webhook_url, tipo, nombre):
    """Helper interno: recibe especificacion_id, llama webhook, retorna respuesta."""
    try:
        data = json.loads(request.body)
        especificacion_id = data.get('especificacion_id')

        if not especificacion_id:
            return JsonResponse({'success': False, 'error': 'El ID de la especificación técnica es requerido'}, status=400)

        try:
            especificacion = EspecificacionTecnica.objects.get(id=especificacion_id)
        except EspecificacionTecnica.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No se encontró la especificación técnica'}, status=404)

        payload = {**_payload_base(especificacion), 'tipo': tipo}
        response_data = llamar_webhook(webhook_url, payload)

        return JsonResponse({'success': True, 'especificacion_id': especificacion.id, 'response_data': response_data})

    except requests.exceptions.Timeout:
        return JsonResponse({'success': False, 'error': 'La solicitud tardó demasiado tiempo.'}, status=408)
    except requests.exceptions.RequestException as e:
        logger.error(f"RequestException en {nombre}: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Error al comunicarse con la API.'}, status=500)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado en {nombre}: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Error interno del servidor.'}, status=500)


@login_required
@require_http_methods(["POST"])
def parametros_material_view(request):
    """Paso 1-1: Parámetros de material."""
    return _sub_paso_view(request, N8N_WEBHOOK_PARAMETROS_URL, 'parametros_material', 'parametros_material_view')


@login_required
@require_http_methods(["POST"])
def parametros_ejecucion_view(request):
    """Paso 1-2: Parámetros de ejecución."""
    return _sub_paso_view(request, N8N_WEBHOOK_PARAMETROS_URL, 'parametros_ejecucion', 'parametros_ejecucion_view')


@login_required
@require_http_methods(["POST"])
def normas_aplicables_view(request):
    """Paso 1-3: Normas aplicables."""
    return _sub_paso_view(request, N8N_WEBHOOK_PARAMETROS_URL, 'normas_aplicables', 'normas_aplicables_view')


@login_required
@require_http_methods(["POST"])
def criterios_calidad_view(request):
    """Paso 1-4: Criterios de calidad."""
    return _sub_paso_view(request, N8N_WEBHOOK_PARAMETROS_URL, 'criterios_calidad', 'criterios_calidad_view')


# ── Guardar sub-pasos individuales ────────────────────────────────────────────

_CAMPO_PASO = {
    'parametros_materiales': 2,
    'parametros_ejecucion':  3,
    'normas_aplicables':     4,
    'criterios_calidad':     5,
}

def _guardar_campo_parametros(request, campo, nombre_view):
    """Helper: guarda una lista de parámetros en el campo JSON indicado del modelo."""
    try:
        data = json.loads(request.body)
        especificacion_id = data.get('especificacion_id')
        parametros = data.get('parametros', [])

        if not especificacion_id:
            return JsonResponse({'success': False, 'error': 'El ID de la especificación técnica es requerido'}, status=400)

        especificacion = get_object_or_404(EspecificacionTecnica, id=especificacion_id)
        setattr(especificacion, campo, parametros)
        nuevo_paso = _CAMPO_PASO.get(campo)
        if nuevo_paso and especificacion.paso < nuevo_paso:
            especificacion.paso = nuevo_paso
        especificacion.save(update_fields=[campo, 'paso'])

        return JsonResponse({'success': True, 'especificacion_id': especificacion.id})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        logger.error('Error en %s: %s', nombre_view, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def guardar_parametros_materiales_view(request):
    """Guarda los parámetros materiales (1-1) seleccionados en BD."""
    return _guardar_campo_parametros(request, 'parametros_materiales', 'guardar_parametros_materiales_view')


@login_required
@require_http_methods(["POST"])
def guardar_parametros_ejecucion_view(request):
    """Guarda los parámetros de ejecución (1-2) seleccionados en BD."""
    return _guardar_campo_parametros(request, 'parametros_ejecucion', 'guardar_parametros_ejecucion_view')


@login_required
@require_http_methods(["POST"])
def guardar_normas_aplicables_view(request):
    """Guarda las normas aplicables (1-3) seleccionadas en BD."""
    return _guardar_campo_parametros(request, 'normas_aplicables', 'guardar_normas_aplicables_view')


@login_required
@require_http_methods(["POST"])
def guardar_criterios_calidad_view(request):
    """Guarda los criterios de calidad (1-4) seleccionados en BD."""
    return _guardar_campo_parametros(request, 'criterios_calidad', 'guardar_criterios_calidad_view')


# ── Paso 2: Parámetros técnicos ────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def confirmar_parametros_view(request):
    """
    Paso 2: Guarda los parámetros seleccionados en BD.
    El frontend luego llama a paso3/propuesta/ para obtener el título sugerido.
    """
    try:
        data = json.loads(request.body)
        parametros_seleccionados = data.get('parametros', [])
        especificacion_id = data.get('especificacion_id')

        if not especificacion_id:
            return JsonResponse({
                'success': False,
                'error': 'El ID de la especificación técnica es requerido'
            }, status=400)

        try:
            especificacion_tecnica = EspecificacionTecnica.objects.get(id=especificacion_id)
        except EspecificacionTecnica.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'No se encontró la especificación técnica relacionada'
            }, status=404)

        # Los parámetros ya se guardan por JSONField en los pasos individuales (guardar_parametros_*_view)
        return JsonResponse({
            'success': True,
            'message': 'Parámetros confirmados exitosamente',
            'especificacion_id': especificacion_tecnica.id,
        })

    except requests.exceptions.Timeout:
        logger.error("Timeout en enviar_parametros_seleccionados_view")
        return JsonResponse({
            'success': False,
            'error': 'La solicitud tardó demasiado tiempo. Por favor, intente nuevamente.'
        }, status=408)
    except requests.exceptions.RequestException as e:
        logger.error(f"RequestException en enviar_parametros_seleccionados_view: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Error al comunicarse con la API. Por favor, intente nuevamente más tarde.'
        }, status=500)
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError en enviar_parametros_seleccionados_view: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado en enviar_parametros_seleccionados_view: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor. Por favor, contacte al administrador o intente nuevamente más tarde.'
        }, status=500)


# ── Paso 3: Título ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def propuesta_titulo_view(request):
    """
    Paso 3 (preparación): Llama al webhook de título para obtener nombre sugerido.
    El frontend llama aquí tras confirmar_parametros, luego muestra el modal al usuario.
    """
    try:
        data = json.loads(request.body)
        especificacion_id = data.get('especificacion_id')

        if not especificacion_id:
            return JsonResponse({'success': False, 'error': 'El ID de la especificación técnica es requerido'}, status=400)

        try:
            especificacion_tecnica = EspecificacionTecnica.objects.get(id=especificacion_id)
        except EspecificacionTecnica.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No se encontró la especificación técnica'}, status=404)

        payload = {
            'titulo': especificacion_tecnica.titulo,
            'descripcion': especificacion_tecnica.descripcion,
            'parametros_materiales': especificacion_tecnica.parametros_materiales or [],
        }

        response_data = llamar_webhook(N8N_WEBHOOK_TITULO_URL, payload, timeout=60)

        titulo_inicial = ''
        titulo_propuesto = ''
        resume_url = ''
        if isinstance(response_data, dict):
            titulo_inicial = response_data.get('titulo_inicial', '')
            titulo_propuesto = response_data.get('titulo_propuesto', '')
            resume_url = response_data.get('resume_url', '')

        return JsonResponse({
            'success': True,
            'titulo_inicial': titulo_inicial,
            'titulo_propuesto': titulo_propuesto,
            'resume_url': resume_url,
            'response_data': response_data,
        })

    except requests.exceptions.Timeout:
        return JsonResponse({'success': False, 'error': 'La solicitud tardó demasiado tiempo (timeout).'}, status=408)
    except requests.exceptions.RequestException as e:
        detail = str(e)
        logger.error(f"RequestException en propuesta_titulo_view: {detail}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Error del webhook: {detail}'}, status=502)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        detail = str(e)
        logger.error(f"Error inesperado en propuesta_titulo_view: {detail}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Error interno: {detail}'}, status=500)


@login_required
@require_http_methods(["POST"])
def guardar_titulo_view(request):
    """
    Paso 3: Guarda el título ajustado en BD y llama al webhook de actividades adicionales.
    """
    try:
        data = json.loads(request.body)
        titulo_final = data.get('titulo_final', '').strip()
        aceptar = data.get('aceptar', False)
        especificacion_id = data.get('especificacion_id')

        if not titulo_final:
            return JsonResponse({'success': False, 'error': 'El título final es requerido'}, status=400)
        if not especificacion_id:
            return JsonResponse({'success': False, 'error': 'El ID de la especificación técnica es requerido'}, status=400)

        try:
            especificacion_tecnica = EspecificacionTecnica.objects.get(id=especificacion_id)
        except EspecificacionTecnica.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No se encontró la especificación técnica'}, status=404)

        if aceptar:
            especificacion_tecnica.titulo = titulo_final
        if especificacion_tecnica.paso < 6:
            especificacion_tecnica.paso = 6
        especificacion_tecnica.save(update_fields=['titulo', 'paso'] if aceptar else ['paso'])

        # Llamar al webhook de actividades adicionales con los datos actualizados
        payload_adicionales = {
            'titulo': especificacion_tecnica.titulo,
            'descripcion': especificacion_tecnica.descripcion,
            'parametros_materiales': especificacion_tecnica.parametros_materiales or [],
            'parametros_ejecucion': especificacion_tecnica.parametros_ejecucion or [],
        }
        try:
            adicionales_response = llamar_webhook(N8N_WEBHOOK_ADICIONALES_URL, payload_adicionales, timeout=120)
        except Exception as e:
            logger.error(f"Error llamando webhook adicionales: {str(e)}", exc_info=True)
            adicionales_response = {}

        # Extraer y guardar resumen de la respuesta
        resumen = None
        if isinstance(adicionales_response, dict):
            resumen = adicionales_response.get('resumen')
        elif isinstance(adicionales_response, list) and adicionales_response:
            first = adicionales_response[0]
            if isinstance(first, dict):
                resumen = first.get('resumen') or (
                    first.get('output', {}).get('resumen') if isinstance(first.get('output'), dict) else None
                )

        if resumen:
            especificacion_tecnica.resumen = resumen
            especificacion_tecnica.save(update_fields=['resumen'])
            logger.info(f"resumen guardada para especificacion {especificacion_id}")

        return JsonResponse({
            'success': True,
            'titulo': especificacion_tecnica.titulo,
            'especificacion_id': especificacion_id,
            'adicionales_response': adicionales_response,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado en guardar_titulo_view: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Error interno del servidor.'}, status=500)


# ── Paso 4: Actividades ────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def adicionales_view(request):
    """
    Paso 4 (preparación): Llama al webhook de actividades adicionales.
    El frontend llama aquí tras guardar_titulo, luego muestra las actividades al usuario.
    """
    try:
        data = json.loads(request.body)
        especificacion_id = data.get('especificacion_id')

        if not especificacion_id:
            return JsonResponse({'success': False, 'error': 'El ID de la especificación técnica es requerido'}, status=400)

        try:
            especificacion_tecnica = EspecificacionTecnica.objects.get(id=especificacion_id)
        except EspecificacionTecnica.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No se encontró la especificación técnica'}, status=404)

        payload = {
            'titulo': especificacion_tecnica.titulo,
            'descripcion': especificacion_tecnica.descripcion,
            'parametros_materiales': especificacion_tecnica.parametros_materiales or [],
            'parametros_ejecucion': especificacion_tecnica.parametros_ejecucion or [],
        }

        response_data = llamar_webhook(N8N_WEBHOOK_ADICIONALES_URL, payload, timeout=120)

        return JsonResponse({'success': True, 'adicionales_response': response_data})

    except requests.exceptions.Timeout:
        return JsonResponse({'success': False, 'error': 'La solicitud tardó demasiado tiempo.'}, status=408)
    except requests.exceptions.RequestException as e:
        logger.error(f"RequestException en adicionales_view: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Error al comunicarse con la API.'}, status=500)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado en adicionales_view: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Error interno del servidor.'}, status=500)


@login_required
@require_http_methods(["POST"])
def actividades_view(request):
    """
    Paso 4: Guarda las actividades seleccionadas en BD.
    El frontend luego llama a paso5/generar/ para generar el resultado final.
    """
    try:
        data = json.loads(request.body)
        actividades_seleccionadas = data.get('actividades', [])
        especificacion_id = data.get('especificacion_id')

        if not especificacion_id:
            return JsonResponse({
                'success': False,
                'error': 'El ID de la especificación técnica es requerido'
            }, status=400)

        try:
            especificacion_tecnica = EspecificacionTecnica.objects.get(id=especificacion_id)
        except EspecificacionTecnica.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'No se encontró la especificación técnica base para vincular las actividades. Asegúrese de haber completado los pasos anteriores.'
            }, status=404)

        # Guardar actividades en el JSONField de EspecificacionTecnica
        actividades_normalizadas = [
            {
                'nombre': a.get('nombre', ''),
                'unidad_medida': a.get('unidad_medida', ''),
                'descripcion': a.get('descripcion', ''),
            }
            for a in actividades_seleccionadas
        ]
        especificacion_tecnica.actividades_adicionales = actividades_normalizadas
        if especificacion_tecnica.paso < 7:
            especificacion_tecnica.paso = 7
        especificacion_tecnica.save(update_fields=['actividades_adicionales', 'paso'])

        logger.info(f"Actividades guardadas exitosamente: {len(actividades_normalizadas)} actividades")

        return JsonResponse({
            'success': True,
            'actividades_guardadas': len(actividades_normalizadas),
            'especificacion_id': especificacion_id,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado en actividades_view: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Error interno del servidor.'}, status=500)


# ── Paso 5: Generar y mostrar resultado ───────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def generar_resultado_view(request):
    """
    Paso 5 (generación): Llama al webhook final para generar el pliego en markdown.
    El frontend llama aquí tras actividades_view, luego llama a paso5/resultado/ para renderizar.
    """
    try:
        data = json.loads(request.body)
        especificacion_id = data.get('especificacion_id')

        if not especificacion_id:
            return JsonResponse({'success': False, 'error': 'El ID de la especificación técnica es requerido'}, status=400)

        try:
            especificacion_tecnica = EspecificacionTecnica.objects.get(id=especificacion_id)
        except EspecificacionTecnica.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No se encontró la especificación técnica'}, status=404)

        especificacion_tecnica.refresh_from_db()

        actividades_raw = especificacion_tecnica.actividades_adicionales or []
        actividades_formateadas = [
            {
                'nombre': act.get('nombre', ''),
                'unidad_medida': act.get('unidad_medida', ''),
                'descripcion': act.get('descripcion', '')
            }
            for act in actividades_raw
        ]

        payload = {
            'titulo': especificacion_tecnica.titulo,
            'descripcion': especificacion_tecnica.descripcion,
            'resumen': especificacion_tecnica.resumen or '',
            'unidad_medida': especificacion_tecnica.unidad_medida or '',
            'parametros_materiales': especificacion_tecnica.parametros_materiales or [],
            'parametros_ejecucion': especificacion_tecnica.parametros_ejecucion or [],
            'normas_aplicables': especificacion_tecnica.normas_aplicables or [],
            'criterios_calidad': especificacion_tecnica.criterios_calidad or [],
            'actividades_adicionales': actividades_formateadas,
        }

        response_data = llamar_webhook(N8N_WEBHOOK_FINAL_URL, payload, timeout=120)

        # Extraer markdown de la respuesta
        markdown_resultado = None
        unidad_respuesta = ''
        if isinstance(response_data, list) and response_data:
            first = response_data[0]
            if isinstance(first, dict):
                markdown_resultado = first.get('pliego') or first.get('output') or first.get('response') or first.get('actividades_adicionales')
                unidad_respuesta = first.get('unidad', '')
        elif isinstance(response_data, dict):
            markdown_resultado = response_data.get('pliego') or response_data.get('output') or response_data.get('response') or response_data.get('actividades_adicionales')
            unidad_respuesta = response_data.get('unidad', '')

        if not markdown_resultado:
            logger.warning("No se encontró markdown en la respuesta del webhook final")
            return JsonResponse({'success': False, 'error': 'No se generó contenido en la respuesta', 'response_data': response_data}, status=502)

        especificacion_tecnica.resultado_markdown = markdown_resultado
        especificacion_tecnica.paso = 8
        especificacion_tecnica.save(update_fields=['resultado_markdown', 'paso'])
        logger.info(f"Markdown guardado: {len(markdown_resultado)} caracteres")

        extensions = [
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.tables',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists',
        ]
        markdown_html = markdown.markdown(markdown_resultado, output_format='html', extensions=extensions)

        return JsonResponse({
            'success': True,
            'markdown_html': markdown_html,
            'raw_markdown': markdown_resultado,
            'especificacion_id': especificacion_id,
            'unidad': unidad_respuesta,
        })

    except requests.exceptions.Timeout:
        return JsonResponse({'success': False, 'error': 'La solicitud tardó demasiado tiempo.'}, status=408)
    except requests.exceptions.RequestException as e:
        logger.error(f"RequestException en generar_resultado_view: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Error al comunicarse con la API.'}, status=500)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado en generar_resultado_view: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Error interno del servidor.'}, status=500)


@login_required
def paso8_resultado_view(request):
    """
    Vista AJAX para obtener el resultado del paso 5 (markdown renderizado)
    """
    try:
        proyecto_id = request.GET.get('proyecto_id')
        if proyecto_id:
            try:
                proyecto_id = int(proyecto_id)
                from proyectos.models import Proyecto
                proyecto = Proyecto.objects.get(id=proyecto_id, activo=True)
                if proyecto.creado_por == request.user or proyecto.publico:
                    request.session['pliego_proyecto_id'] = proyecto_id
                    request.session.modified = True
                    logger.info(f"paso8_resultado_view - Proyecto ID {proyecto_id} guardado en sesión")
            except (ValueError, Proyecto.DoesNotExist) as e:
                logger.warning(f"paso8_resultado_view - Proyecto no válido o no encontrado: {str(e)}")
            except Exception as e:
                logger.error(f"paso8_resultado_view - Error al procesar proyecto_id: {str(e)}", exc_info=True)

        proyecto_id_sesion = request.session.get('pliego_proyecto_id')
        if proyecto_id_sesion:
            logger.info(f"paso8_resultado_view - Proyecto ID {proyecto_id_sesion} encontrado en sesión")
            request.session.modified = True

        especificacion_id = request.GET.get('especificacion_id') or request.POST.get('especificacion_id')

        if not especificacion_id and request.body:
            try:
                data = json.loads(request.body)
                especificacion_id = data.get('especificacion_id')
            except (json.JSONDecodeError, AttributeError):
                pass

        if not especificacion_id:
            return JsonResponse({
                'success': False,
                'error': 'El ID de la especificación técnica es requerido'
            }, status=400)

        try:
            especificacion_tecnica = EspecificacionTecnica.objects.get(
                id=especificacion_id,
                resultado_markdown__isnull=False
            )
            if not especificacion_tecnica.resultado_markdown:
                raise EspecificacionTecnica.DoesNotExist
        except EspecificacionTecnica.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'No se encontró el resultado de la especificación técnica. Asegúrese de haber completado todos los pasos anteriores.'
            }, status=404)

        extensions = [
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.tables',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists'
        ]
        markdown_html = markdown.markdown(
            especificacion_tecnica.resultado_markdown,
            output_format='html',
            extensions=extensions
        )

        return JsonResponse({
            'success': True,
            'markdown_html': markdown_html,
            'raw_markdown': especificacion_tecnica.resultado_markdown,
            'titulo': especificacion_tecnica.titulo,
        })

    except Exception as e:
        logger.error(f"Error inesperado en paso8_resultado_view: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor. Por favor, contacte al administrador o intente nuevamente más tarde.'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def guardar_resultado_view(request):
    """
    Vista AJAX para guardar el resultado final.
    Si hay un proyecto_id en la sesión, convierte EspecificacionTecnica en Especificacion.
    """
    try:
        data = json.loads(request.body)
        contenido_enviado = data.get('contenido', '').strip()
        especificacion_id = data.get('especificacion_id')

        logger.info(f"guardar_resultado_view - especificacion_id recibido: {especificacion_id}")
        logger.info(f"guardar_resultado_view - contenido recibido en payload: {len(contenido_enviado) if contenido_enviado else 0} caracteres")

        if not especificacion_id:
            logger.warning("guardar_resultado_view - especificacion_id faltante")
            return JsonResponse({
                'success': False,
                'error': 'El ID de la especificación técnica es requerido'
            }, status=400)

        try:
            especificacion_tecnica = EspecificacionTecnica.objects.get(id=especificacion_id)
            logger.info(f"guardar_resultado_view - EspecificacionTecnica encontrada: {especificacion_tecnica.titulo}")
        except EspecificacionTecnica.DoesNotExist:
            logger.error(f"guardar_resultado_view - EspecificacionTecnica no encontrada con id: {especificacion_id}")
            return JsonResponse({
                'success': False,
                'error': 'No se encontró la especificación técnica relacionada.'
            }, status=404)

        if contenido_enviado:
            contenido = contenido_enviado
            logger.info(f"guardar_resultado_view - Usando contenido del payload: {len(contenido)} caracteres")
        elif especificacion_tecnica.resultado_markdown:
            contenido = especificacion_tecnica.resultado_markdown
            logger.info(f"guardar_resultado_view - Usando resultado_markdown de la BD: {len(contenido)} caracteres")
        else:
            logger.error("guardar_resultado_view - No hay contenido disponible")
            return JsonResponse({
                'success': False,
                'error': 'No se encontró el contenido de la especificación. Asegúrese de haber completado todos los pasos anteriores.'
            }, status=400)

        logger.info(f"guardar_resultado_view - INICIANDO GUARDADO - {len(contenido)} caracteres")

        try:
            contenido_anterior = especificacion_tecnica.resultado_markdown or ''
            especificacion_tecnica.resultado_markdown = contenido
            especificacion_tecnica.save(update_fields=['resultado_markdown'])
            logger.info(f"guardar_resultado_view - ✅ save() ejecutado")

            from django.db import transaction
            transaction.commit()
            logger.info(f"guardar_resultado_view - ✅ Transacción confirmada")
        except Exception as e:
            logger.error(f"guardar_resultado_view - ❌ Error en save(): {str(e)}", exc_info=True)
            raise

        especificacion_tecnica.refresh_from_db()
        contenido_despues_save = especificacion_tecnica.resultado_markdown or ''

        if contenido_despues_save != contenido:
            logger.warning(f"guardar_resultado_view - ⚠️ Contenido no coincide después de save(). Intentando con update()...")
            try:
                filas_actualizadas = EspecificacionTecnica.objects.filter(id=especificacion_id).update(resultado_markdown=contenido)
                logger.info(f"guardar_resultado_view - ✅ update() ejecutado. Filas: {filas_actualizadas}")
                especificacion_tecnica.refresh_from_db()
                contenido_guardado = especificacion_tecnica.resultado_markdown or ''
            except Exception as e:
                logger.error(f"guardar_resultado_view - ❌ Error en update(): {str(e)}", exc_info=True)
                contenido_guardado = contenido_despues_save
        else:
            contenido_guardado = contenido_despues_save
            logger.info(f"guardar_resultado_view - ✅ save() funcionó correctamente")

        guardado_exitoso = contenido_guardado == contenido
        logger.info(f"guardar_resultado_view - Guardado exitoso: {guardado_exitoso} ({len(contenido_guardado)} chars)")

        # Verificación final
        especificacion_tecnica.refresh_from_db()
        verificacion_final = especificacion_tecnica.resultado_markdown or ''

        if len(verificacion_final) == 0:
            logger.error(f"guardar_resultado_view - ERROR CRÍTICO: resultado_markdown está vacío en la BD")
            return JsonResponse({
                'success': False,
                'error': 'No se pudo guardar el contenido de la especificación.',
                'especificacion_id': especificacion_tecnica.id,
            }, status=500)

        # Vincular con proyecto si hay proyecto_id en sesión
        proyecto_id = request.session.get('pliego_proyecto_id')
        redirect_url = None

        if not proyecto_id:
            for source in [data.get('proyecto_id'), request.GET.get('proyecto_id')]:
                if source:
                    try:
                        proyecto_id = int(source)
                        request.session['pliego_proyecto_id'] = proyecto_id
                        request.session.modified = True
                        logger.info(f"guardar_resultado_view - proyecto_id obtenido: {proyecto_id}")
                        break
                    except (ValueError, TypeError):
                        pass

        if proyecto_id:
            try:
                from proyectos.models import Proyecto, Especificacion
                from django.core.files.base import ContentFile
                from django.utils.text import slugify
                from django.utils import timezone
                from django.urls import reverse

                proyecto = Proyecto.objects.get(id=proyecto_id, activo=True)

                if proyecto.creado_por != request.user and not proyecto.publico:
                    return JsonResponse({
                        'success': False,
                        'error': 'No tiene permisos para guardar en este proyecto'
                    }, status=403)

                slug = slugify(especificacion_tecnica.titulo) or 'especificacion'
                timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
                filename = f"{slug}-{timestamp}.md"
                unidad_medida = especificacion_tecnica.unidad_medida or 'glb'

                especificacion = Especificacion(
                    proyecto=proyecto,
                    titulo=especificacion_tecnica.titulo,
                    contenido=contenido,
                    unidad_medida=unidad_medida,
                    actividades_adicionales=especificacion_tecnica.actividades_adicionales,
                )
                especificacion.archivo.save(filename, ContentFile(contenido), save=True)

                request.session.pop('pliego_proyecto_id', None)
                redirect_url = reverse('proyectos:proyecto_detalle', args=[proyecto.id]) + '?guardado=1'

            except Proyecto.DoesNotExist:
                request.session.pop('pliego_proyecto_id', None)
            except Exception as e:
                logger.error(f"Error al convertir EspecificacionTecnica a Especificacion: {str(e)}", exc_info=True)

        if not redirect_url and proyecto_id:
            try:
                from django.urls import reverse
                redirect_url = reverse('proyectos:proyecto_detalle', args=[proyecto_id]) + '?guardado=1'
            except Exception as e:
                logger.error(f"guardar_resultado_view - Error al crear redirect_url: {str(e)}")

        return JsonResponse({
            'success': True,
            'message': 'Especificación guardada exitosamente',
            'especificacion_id': especificacion_tecnica.id,
            'redirect_url': redirect_url,
            'proyecto_id': proyecto_id,
        })

    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError en guardar_resultado_view: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado en guardar_resultado_view: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor. Por favor, contacte al administrador o intente nuevamente más tarde.'
        }, status=500)


# ── Utilidades ─────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def actualizar_cantidad_especificacion_tecnica_view(request, especificacion_tecnica_id):
    """
    Vista AJAX para actualizar la cantidad de una EspecificacionTecnica
    """
    try:
        especificacion_tecnica = get_object_or_404(EspecificacionTecnica, id=especificacion_tecnica_id)

        if especificacion_tecnica.creado_por and especificacion_tecnica.creado_por != request.user:
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para editar esta especificación técnica'
            }, status=403)

        data = json.loads(request.body)
        cantidad = data.get('cantidad', '').strip()

        if len(cantidad) > 10:
            cantidad = cantidad[:10]

        especificacion_tecnica.cantidad = cantidad if cantidad else None
        especificacion_tecnica.save(update_fields=['cantidad'])

        logger.info(f"Cantidad actualizada para EspecificacionTecnica {especificacion_tecnica_id}: '{cantidad}'")

        return JsonResponse({
            'success': True,
            'cantidad': especificacion_tecnica.cantidad or ''
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f"Error al actualizar cantidad de EspecificacionTecnica: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def eliminar_especificacion_tecnica_view(request, especificacion_tecnica_id):
    """
    Soft-delete: marca la EspecificacionTecnica como eliminada.
    """
    try:
        updated = EspecificacionTecnica.objects.filter(
            id=especificacion_tecnica_id,
            creado_por=request.user,
        ).update(eliminado=True)
        if updated:
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'No encontrada o sin permisos'}, status=404)
    except Exception as e:
        logger.error(f"eliminar_especificacion_tecnica_view - {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_especificacion_datos_view(request, especificacion_tecnica_id):
    """
    Devuelve los datos guardados de una EspecificacionTecnica para reanudar un borrador.
    """
    try:
        spec = EspecificacionTecnica.objects.get(
            id=especificacion_tecnica_id,
            creado_por=request.user,
            eliminado=False,
        )
        return JsonResponse({
            'id': spec.id,
            'titulo': spec.titulo,
            'descripcion': spec.descripcion,
            'tipo_servicio': spec.tipo_servicio,
            'unidad_medida': spec.unidad_medida or '',
            'paso': spec.paso,
            'clasificacion': spec.clasificacion,
            'parametros_materiales': spec.parametros_materiales or [],
            'parametros_ejecucion': spec.parametros_ejecucion or [],
            'normas_aplicables': spec.normas_aplicables or [],
            'criterios_calidad': spec.criterios_calidad or [],
            'actividades_adicionales': spec.actividades_adicionales or [],
        })
    except EspecificacionTecnica.DoesNotExist:
        return JsonResponse({'error': 'No encontrada o sin permisos'}, status=404)
    except Exception as e:
        logger.error(f"get_especificacion_datos_view - {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


