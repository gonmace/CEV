from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.files import File
import json
import os
import requests
import re
import logging
from PIL import Image
from accounts.permissions import puede_editar, puede_ver
from core.n8n import N8NError, extraer_markdown, limpiar_markdown_ubicacion, llamar_webhook_seguro, webhook_url
from proyectos.models import Proyecto
from .models import Ubicacion, UbicacionImagen
from .forms import UbicacionForm, UbicacionContenidoForm

logger = logging.getLogger(__name__)

N8N_WEBHOOK_UBICACION_URL = webhook_url('ubicacion')




def obtener_indicaciones_ruta(origen_lat, origen_lon, destino_lat, destino_lon, google_maps_api_key):
    """
    Obtiene las indicaciones de ruta desde un origen hasta un destino usando Google Directions API
    Retorna un diccionario con las indicaciones formateadas
    """
    try:
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            'origin': f"{origen_lat},{origen_lon}",
            'destination': f"{destino_lat},{destino_lon}",
            'key': google_maps_api_key,
            'language': 'es',
            'alternatives': 'false'  # Solo la ruta principal
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data['status'] == 'OK' and data['routes']:
            route = data['routes'][0]
            legs = route.get('legs', [])
            if legs:
                leg = legs[0]
                steps = leg.get('steps', [])
                
                # Extraer información de la ruta
                distancia_total = leg.get('distance', {}).get('text', '')
                duracion_total = leg.get('duration', {}).get('text', '')
                
                # Procesar los pasos de las indicaciones
                indicaciones = []
                for step in steps:
                    html_instructions = step.get('html_instructions', '')
                    # Limpiar HTML de las instrucciones
                    texto_limpio = re.sub(r'<[^>]+>', '', html_instructions)
                    distancia = step.get('distance', {}).get('text', '')
                    indicaciones.append({
                        'instruccion': texto_limpio,
                        'distancia': distancia
                    })
                
                return {
                    'distancia_total': distancia_total,
                    'duracion_total': duracion_total,
                    'vias': route.get('summary', ''),
                    'indicaciones': indicaciones,
                    'pasos_totales': len(steps)
                }
    except Exception as e:
        logger.error(f"Error al obtener indicaciones: {e}")
    
    return None


class RutaError(Exception):
    """Fallo al obtener la ruta desde el centro de la ciudad, con mensaje para el usuario."""


def construir_resumen_ruta(ciudad, vias, distancia, duracion):
    """Arma un párrafo genérico de acceso al sitio. Determinista: sin IA, sin pasos."""
    base = f"El acceso al sitio se realiza desde el centro de {ciudad}"
    if vias:
        base += f" por {vias}"
    base += "."
    datos = []
    if distancia:
        datos.append(f"una distancia aproximada de {distancia}")
    if duracion:
        datos.append(f"un tiempo estimado de viaje de {duracion} en vehículo")
    if datos:
        base += " El recorrido comprende " + " y ".join(datos) + "."
    return base


def obtener_datos_ruta(ubicacion_instance, google_maps_api_key):
    """Geocodifica la ciudad, consulta Directions y setea los campos ruta_* de la ubicación.

    No guarda la instancia (el caller decide cuándo). Lanza RutaError con mensaje en
    español si la ciudad no se puede geocodificar o no hay ruta.
    """
    if not ubicacion_instance.ciudad:
        raise RutaError("La ubicación no tiene ciudad definida; no se puede calcular la ruta.")
    if ubicacion_instance.latitud is None or ubicacion_instance.longitud is None:
        raise RutaError("La ubicación no tiene coordenadas; no se puede calcular la ruta.")

    try:
        geocoding_response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={'address': ubicacion_instance.ciudad, 'key': google_maps_api_key},
            timeout=10,
        )
        geocoding_data = geocoding_response.json()
    except Exception as e:
        logger.error(f"Error al geocodificar la ciudad '{ubicacion_instance.ciudad}': {e}")
        raise RutaError("No se pudo consultar Google Maps para ubicar el centro de la ciudad.")

    if geocoding_data.get('status') != 'OK' or not geocoding_data.get('results'):
        raise RutaError(f'No se encontró la ciudad "{ubicacion_instance.ciudad}" en Google Maps. Revisa el nombre.')

    centro = geocoding_data['results'][0]['geometry']['location']
    ruta = obtener_indicaciones_ruta(
        centro['lat'], centro['lng'],
        float(ubicacion_instance.latitud), float(ubicacion_instance.longitud),
        google_maps_api_key,
    )
    if not ruta:
        raise RutaError("Google Maps no devolvió una ruta desde el centro de la ciudad hasta el sitio.")

    ubicacion_instance.ruta_vias = ruta.get('vias', '')[:255]
    ubicacion_instance.ruta_distancia = ruta.get('distancia_total', '')[:50]
    ubicacion_instance.ruta_duracion = ruta.get('duracion_total', '')[:50]
    ubicacion_instance.ruta_resumen = construir_resumen_ruta(
        ubicacion_instance.ciudad,
        ubicacion_instance.ruta_vias,
        ubicacion_instance.ruta_distancia,
        ubicacion_instance.ruta_duracion,
    )


def crear_imagen_mapa(ubicacion_instance, google_maps_api_key=None):
    """
    Descarga y guarda la imagen del mapa desde Google Static Maps API
    """
    if not google_maps_api_key:
        # Intentar obtener desde settings primero, luego desde env
        google_maps_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        if not google_maps_api_key:
            google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
    
    if not google_maps_api_key:
        raise ValueError("Google Maps API Key no configurada. Por favor, agregue GOOGLE_MAPS_API_KEY en su archivo .env o en la configuración de Django.")
    
    latitud = float(ubicacion_instance.latitud)
    longitud = float(ubicacion_instance.longitud)
    
    # Crear directorio temporal si no existe
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'ubicaciones', 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    mapa_imagen_path = os.path.join(temp_dir, f'mapa_{ubicacion_instance.id}.png')
    
    # Inferir zoom óptimo
    zoom = 16
    
    # Construir URL de Google Static Maps
    mapa_url = (
        f"https://maps.googleapis.com/maps/api/staticmap?"
        f"center={latitud},{longitud}&"
        f"zoom={zoom}&"
        f"size=1280x720&"
        f"maptype=satellite&"
        f"markers=color:red|{latitud},{longitud}&"
        f"key={google_maps_api_key}"
    )
    
    # Descargar imagen del mapa
    try:
        response = requests.get(mapa_url, timeout=30)
        
        # Verificar el código de estado HTTP
        if response.status_code == 403:
            # Intentar obtener más información del error
            try:
                error_data = response.json()
                error_message = error_data.get('error_message', 'Acceso denegado')
            except:
                error_message = response.text[:200] if response.text else 'Acceso denegado'
            
            raise Exception(
                f"Error 403 - Acceso denegado a Google Maps API. "
                f"Verifique que:\n"
                f"1. La API key sea válida y completa\n"
                f"2. La API 'Maps Static API' esté habilitada en Google Cloud Console\n"
                f"3. No haya restricciones de IP o dominio en la API key\n"
                f"4. La API key tenga los permisos necesarios\n"
                f"Error detallado: {error_message}"
            )
        elif response.status_code == 400:
            try:
                error_data = response.json()
                error_message = error_data.get('error_message', 'Solicitud inválida')
            except:
                error_message = response.text[:200] if response.text else 'Solicitud inválida'
            
            raise Exception(
                f"Error 400 - Solicitud inválida a Google Maps API. "
                f"Verifique las coordenadas (latitud: {latitud}, longitud: {longitud}). "
                f"Error: {error_message}"
            )
        
        response.raise_for_status()
        
        # Verificar que la respuesta sea una imagen
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type:
            raise Exception(
                f"La respuesta no es una imagen. Content-Type: {content_type}. "
                f"Respuesta: {response.text[:200]}"
            )
        
        # Guardar imagen temporalmente
        with open(mapa_imagen_path, 'wb') as f:
            f.write(response.content)
        
        # Verificar que el archivo se guardó correctamente
        if not os.path.exists(mapa_imagen_path) or os.path.getsize(mapa_imagen_path) == 0:
            raise Exception("No se pudo guardar la imagen del mapa correctamente")
        
        # Guardar imagen en el modelo
        with open(mapa_imagen_path, 'rb') as img_file:
            ubicacion_instance.mapa_imagen.save(
                f'mapa_{ubicacion_instance.id}.png',
                File(img_file),
                save=False
            )
        
        # Eliminar archivo temporal
        if os.path.exists(mapa_imagen_path):
            os.remove(mapa_imagen_path)
    except requests.exceptions.RequestException as e:
        # Eliminar archivo temporal si existe
        if os.path.exists(mapa_imagen_path):
            os.remove(mapa_imagen_path)
        raise Exception(f"Error de conexión con Google Maps API: {str(e)}")
    except Exception as e:
        # Eliminar archivo temporal si existe
        if os.path.exists(mapa_imagen_path):
            os.remove(mapa_imagen_path)
        # Si el error ya tiene un mensaje descriptivo, re-lanzarlo
        if "Error 403" in str(e) or "Error 400" in str(e):
            raise
        raise Exception(f"Error al descargar el mapa: {str(e)}")


def enviar_a_n8n_ubicacion(ubicacion_instance):
    """
    Envía los datos de la ubicación al webhook de n8n para generar contenido con IA
    y lo deja en `ubicacion_instance.contenido` (no guarda la instancia).
    Lanza N8NError con mensaje en español si el webhook falla o no devuelve contenido.
    """
    proyecto = ubicacion_instance.proyecto
    tiene_coords = ubicacion_instance.latitud is not None and ubicacion_instance.longitud is not None
    payload = {
        'nombre': ubicacion_instance.nombre,
        'descripcion': ubicacion_instance.descripcion or '',
        'latitud': float(ubicacion_instance.latitud) if tiene_coords else None,
        'longitud': float(ubicacion_instance.longitud) if tiene_coords else None,
        # Coordenadas ya formateadas para que el prompt las copie literalmente,
        # sin que el LLM las redondee o trunque.
        'coordenadas_texto': (
            f"{float(ubicacion_instance.latitud):.6f}, {float(ubicacion_instance.longitud):.6f}"
            if tiene_coords else ''
        ),
        'ciudad': ubicacion_instance.ciudad or '',
        'contenido_actual': ubicacion_instance.contenido or '',
        'proyecto_nombre': proyecto.nombre if proyecto else '',
        'proyecto_solicitante': proyecto.solicitante if proyecto else '',
        'proyecto_ubicacion': proyecto.ubicacion if proyecto else '',
        'ruta': {
            'vias': ubicacion_instance.ruta_vias,
            'distancia': ubicacion_instance.ruta_distancia,
            'duracion': ubicacion_instance.ruta_duracion,
            'resumen': ubicacion_instance.ruta_resumen,
        },
        'tiene_ruta': bool(ubicacion_instance.ruta_resumen),
    }

    logger.info(f"Enviando datos de ubicación a n8n webhook: {N8N_WEBHOOK_UBICACION_URL}")
    respuesta = llamar_webhook_seguro(N8N_WEBHOOK_UBICACION_URL, payload, timeout=60)

    markdown_generado = extraer_markdown(respuesta)
    if not markdown_generado:
        logger.warning(f"Sin markdown en la respuesta del webhook de ubicación. Tipo: {type(respuesta)}")
        raise N8NError("La respuesta de la IA no contiene contenido utilizable.")

    ubicacion_instance.contenido = limpiar_markdown_ubicacion(markdown_generado)
    logger.info(f"Contenido markdown generado guardado: {len(ubicacion_instance.contenido)} caracteres")


def _generar_mapa_ruta_contenido(ubicacion, con_contenido=True):
    """Ejecuta las tres etapas de generación (mapa, ruta, contenido IA) por separado.

    Cada etapa falla sin tumbar a las demás. Retorna la lista de mensajes de error
    (vacía si todo salió bien). No guarda la instancia.
    """
    errores = []
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)

    try:
        crear_imagen_mapa(ubicacion, google_maps_api_key=api_key)
    except ValueError:
        errores.append('Falta configurar GOOGLE_MAPS_API_KEY, no se generó el mapa.')
    except Exception as e:
        logger.error(f"Error al generar el mapa de la ubicación {ubicacion.id}: {e}", exc_info=True)
        errores.append('Falló la generación del mapa.')

    try:
        obtener_datos_ruta(ubicacion, api_key)
    except RutaError as e:
        errores.append(f'Falló el cálculo de la ruta: {e}')
    except Exception as e:
        logger.error(f"Error al calcular la ruta de la ubicación {ubicacion.id}: {e}", exc_info=True)
        errores.append('Falló el cálculo de la ruta.')

    if con_contenido:
        try:
            enviar_a_n8n_ubicacion(ubicacion)
        except N8NError as e:
            errores.append(f'Falló la generación del contenido con IA: {e}')
        except Exception as e:
            logger.error(f"Error al generar contenido IA de la ubicación {ubicacion.id}: {e}", exc_info=True)
            errores.append('Falló la generación del contenido con IA.')

    return errores


@login_required
def crear_ubicacion_view(request, proyecto_id):
    """
    Vista para crear una nueva ubicación
    """
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, activo=True)
    
    if not puede_editar(request.user, proyecto):
        messages.error(request, 'Solo puedes crear ubicaciones en tus propios proyectos.')
        return redirect('proyectos:proyecto_detalle', proyecto.id)
    
    if request.method == 'POST':
        form = UbicacionForm(request.POST)
        if form.is_valid():
            ubicacion = form.save(commit=False)
            ubicacion.proyecto = proyecto
            ubicacion.save()

            if ubicacion.latitud and ubicacion.longitud:
                errores = _generar_mapa_ruta_contenido(ubicacion)
                ubicacion.save()
                if not errores:
                    messages.success(request, f'Ubicación "{ubicacion.nombre}" creada. Mapa, ruta y contenido generados.')
                else:
                    messages.warning(
                        request,
                        f'Ubicación "{ubicacion.nombre}" creada, pero con problemas: '
                        + ' '.join(errores)
                        + ' Puedes reintentar con "Regenerar contenido".'
                    )
            else:
                messages.success(request, f'Ubicación "{ubicacion.nombre}" creada exitosamente.')

            return redirect('proyectos:proyecto_detalle', proyecto.id)
    else:
        form = UbicacionForm()
    
    return render(request, 'ubi_web/crear_ubicacion.html', {
        'form': form,
        'proyecto': proyecto,
    })


@login_required
def editar_ubicacion_view(request, ubicacion_id):
    """
    Vista para editar una ubicación existente
    """
    ubicacion = get_object_or_404(Ubicacion, id=ubicacion_id, proyecto__activo=True)
    proyecto = ubicacion.proyecto
    
    if not puede_editar(request.user, proyecto):
        messages.error(request, 'Solo puedes editar ubicaciones de tus proyectos.')
        return redirect('proyectos:proyecto_detalle', proyecto.id)
    
    if request.method == 'POST':
        form = UbicacionForm(request.POST, instance=ubicacion)
        if form.is_valid():
            cambio_geo = bool({'coordenadas', 'ciudad'} & set(form.changed_data))
            ubicacion = form.save()
            # Al cambiar coordenadas o ciudad se regeneran mapa y ruta, pero NO el
            # contenido: eso pisaría ediciones manuales (hay botón "Regenerar contenido").
            if cambio_geo and ubicacion.latitud and ubicacion.longitud:
                errores = _generar_mapa_ruta_contenido(ubicacion, con_contenido=False)
                ubicacion.save()
                if not errores:
                    messages.success(request, 'Ubicación actualizada. Mapa y ruta regenerados.')
                else:
                    messages.warning(request, 'Ubicación actualizada, pero con problemas: ' + ' '.join(errores))
            else:
                messages.success(request, 'Ubicación actualizada correctamente.')
            return redirect('proyectos:proyecto_detalle', proyecto.id)
    else:
        form = UbicacionForm(instance=ubicacion)
    
    return render(request, 'ubi_web/editar_ubicacion.html', {
        'form': form,
        'ubicacion': ubicacion,
        'proyecto': proyecto,
    })


@login_required
@require_http_methods(["POST"])
def regenerar_contenido_ubicacion_view(request, ubicacion_id):
    """Recalcula la ruta y vuelve a generar el contenido de la ubicación con IA."""
    ubicacion = get_object_or_404(Ubicacion, id=ubicacion_id, proyecto__activo=True)
    proyecto = ubicacion.proyecto

    if not puede_editar(request.user, proyecto):
        messages.error(request, 'Solo puedes regenerar el contenido de ubicaciones de tus proyectos.')
        return redirect('proyectos:proyecto_detalle', proyecto.id)

    if not (ubicacion.latitud and ubicacion.longitud):
        messages.error(request, 'La ubicación no tiene coordenadas; agrégalas antes de regenerar el contenido.')
        return redirect('proyectos:proyecto_detalle', proyecto.id)

    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    try:
        obtener_datos_ruta(ubicacion, api_key)
    except RutaError as e:
        messages.warning(request, f'No se pudo actualizar la ruta: {e}')
    except Exception as e:
        logger.error(f"Error al recalcular la ruta de la ubicación {ubicacion.id}: {e}", exc_info=True)
        messages.warning(request, 'No se pudo actualizar la ruta.')

    try:
        enviar_a_n8n_ubicacion(ubicacion)
        ubicacion.save()
        messages.success(request, f'Contenido de "{ubicacion.nombre}" regenerado con IA.')
    except N8NError as e:
        ubicacion.save()  # conserva la ruta actualizada aunque falle la IA
        messages.error(request, f'No se pudo regenerar el contenido: {e}')
    except Exception as e:
        logger.error(f"Error al regenerar contenido de la ubicación {ubicacion.id}: {e}", exc_info=True)
        ubicacion.save()
        messages.error(request, 'No se pudo regenerar el contenido con IA.')

    return redirect('proyectos:proyecto_detalle', proyecto.id)


@login_required
def editar_contenido_ubicacion_view(request, ubicacion_id):
    """
    Vista para editar el contenido markdown de una ubicación
    """
    ubicacion = get_object_or_404(Ubicacion, id=ubicacion_id, proyecto__activo=True)
    proyecto = ubicacion.proyecto

    if not puede_editar(request.user, proyecto):
        messages.error(request, 'Solo puedes editar el contenido de ubicaciones de tus proyectos.')
        return redirect('proyectos:proyecto_detalle', proyecto.id)

    if request.method == 'POST':
        form = UbicacionContenidoForm(request.POST, instance=ubicacion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contenido de ubicación actualizado correctamente.')
            return redirect('proyectos:proyecto_detalle', proyecto.id)
    else:
        form = UbicacionContenidoForm(instance=ubicacion)

    return render(request, 'ubi_web/editar_contenido_ubicacion.html', {
        'form': form,
        'ubicacion': ubicacion,
        'proyecto': proyecto,
    })


@login_required
def eliminar_ubicacion_view(request, ubicacion_id):
    """
    Vista para eliminar una ubicación
    """
    ubicacion = get_object_or_404(Ubicacion, id=ubicacion_id, proyecto__activo=True)
    proyecto = ubicacion.proyecto
    
    if not puede_editar(request.user, proyecto):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'error': 'Solo puedes eliminar ubicaciones de tus proyectos.'}, status=403)
        messages.error(request, 'Solo puedes eliminar ubicaciones de tus proyectos.')
        return redirect('proyectos:proyecto_detalle', proyecto.id)
    
    if request.method == 'POST':
        # Eliminar todas las imágenes asociadas
        for imagen in ubicacion.imagenes.all():
            if imagen.imagen:
                imagen.imagen.delete(save=False)
        ubicacion.delete()
        
        # Si es una petición AJAX, devolver JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'message': 'Ubicación eliminada correctamente.'
            })
        
        messages.success(request, 'Ubicación eliminada correctamente.')
        return redirect('proyectos:proyecto_detalle', proyecto.id)
    
    # Si es GET, mostrar la página de confirmación (para compatibilidad)
    return render(request, 'ubi_web/eliminar_ubicacion.html', {
        'ubicacion': ubicacion,
        'proyecto': proyecto,
    })


@login_required
def obtener_imagenes_ubicacion_view(request, ubicacion_id):
    """
    Vista AJAX para obtener las imágenes de una ubicación
    """
    ubicacion = get_object_or_404(Ubicacion, id=ubicacion_id, proyecto__activo=True)
    
    # Verificar permisos
    if not puede_ver(request.user, ubicacion.proyecto):
        return JsonResponse({'error': 'No tienes permisos para ver las imágenes de esta ubicación.'}, status=403)
    
    imagenes = ubicacion.imagenes.all()
    imagenes_data = [{
        'id': img.id,
        'url': img.imagen.url if img.imagen else '',
        'descripcion': img.descripcion or '',
        'fecha_subida': img.fecha_subida.strftime('%d/%m/%Y %H:%M')
    } for img in imagenes]
    
    return JsonResponse({
        'success': True,
        'imagenes': imagenes_data
    })


@login_required
@require_http_methods(["POST"])
def subir_imagenes_ubicacion_view(request, ubicacion_id):
    """
    Vista AJAX para subir imágenes a una ubicación
    """
    ubicacion = get_object_or_404(Ubicacion, id=ubicacion_id, proyecto__activo=True)
    
    # Verificar que el usuario puede editar el proyecto
    if not puede_editar(request.user, ubicacion.proyecto):
        return JsonResponse({'error': 'Solo puedes agregar imágenes a ubicaciones de tus proyectos.'}, status=403)
    
    imagenes_subidas = request.FILES.getlist('imagenes')
    
    if not imagenes_subidas:
        return JsonResponse({'error': 'No se proporcionaron imágenes.'}, status=400)
    
    imagenes_creadas = []
    for imagen_file in imagenes_subidas:
        # Validar que sea una imagen
        try:
            img = Image.open(imagen_file)
            img.verify()
            imagen_file.seek(0)  # Resetear el archivo después de verificar
        except Exception:
            continue
        
        ubicacion_imagen = UbicacionImagen(
            ubicacion=ubicacion,
            imagen=imagen_file
        )
        ubicacion_imagen.save()
        imagenes_creadas.append({
            'id': ubicacion_imagen.id,
            'url': ubicacion_imagen.imagen.url
        })
    
    if not imagenes_creadas:
        return JsonResponse({'error': 'No se pudieron procesar las imágenes. Asegúrate de que sean archivos de imagen válidos.'}, status=400)
    
    return JsonResponse({
        'success': True,
        'message': f'{len(imagenes_creadas)} imagen(es) subida(s) correctamente.',
        'imagenes': imagenes_creadas
    })


@login_required
@require_http_methods(["POST"])
def eliminar_imagen_ubicacion_view(request, imagen_id):
    """
    Vista AJAX para eliminar una imagen de una ubicación
    """
    imagen = get_object_or_404(UbicacionImagen, id=imagen_id)
    ubicacion = imagen.ubicacion
    
    # Verificar que el usuario puede editar el proyecto
    if not puede_editar(request.user, ubicacion.proyecto):
        return JsonResponse({'error': 'Solo puedes eliminar imágenes de ubicaciones de tus proyectos.'}, status=403)
    
    # Eliminar el archivo físico
    if imagen.imagen:
        imagen.imagen.delete(save=False)
    
    imagen.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Imagen eliminada correctamente.'
    })


@login_required
@require_http_methods(["POST"])
def actualizar_descripcion_imagen_ubicacion_view(request, imagen_id):
    """
    Vista AJAX para actualizar la descripción de una imagen de ubicación
    """
    imagen = get_object_or_404(UbicacionImagen, id=imagen_id)
    ubicacion = imagen.ubicacion
    
    # Verificar que el usuario puede editar el proyecto
    if not puede_editar(request.user, ubicacion.proyecto):
        return JsonResponse({'error': 'Solo puedes editar descripciones de imágenes de tus proyectos.'}, status=403)
    
    try:
        data = json.loads(request.body)
        descripcion = data.get('descripcion', '').strip()
        
        imagen.descripcion = descripcion
        imagen.save(update_fields=['descripcion'])
        
        return JsonResponse({
            'success': True,
            'message': 'Descripción actualizada correctamente.'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos JSON inválidos.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def descargar_pdf_ubicacion_view(request, ubicacion_id):
    """
    Vista para descargar el PDF de una ubicación
    """
    ubicacion = get_object_or_404(Ubicacion, id=ubicacion_id, proyecto__activo=True)
    
    # Verificar permisos
    if not puede_ver(request.user, ubicacion.proyecto):
        messages.error(request, 'No tienes permisos para descargar el PDF de esta ubicación.')
        return redirect('proyectos:proyecto_detalle', ubicacion.proyecto.id)
    
    if not ubicacion.documento_pdf:
        messages.error(request, 'No hay PDF disponible para esta ubicación.')
        return redirect('proyectos:proyecto_detalle', ubicacion.proyecto.id)
    
    # Verificar que el archivo existe físicamente
    if not os.path.exists(ubicacion.documento_pdf.path):
        messages.error(request, 'El archivo PDF no se encuentra en el servidor.')
        return redirect('proyectos:proyecto_detalle', ubicacion.proyecto.id)
    
    try:
        response = FileResponse(
            open(ubicacion.documento_pdf.path, 'rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="ubicacion_{ubicacion.nombre}_{ubicacion.id}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f'Error al descargar el PDF: {str(e)}')
        return redirect('proyectos:proyecto_detalle', ubicacion.proyecto.id)
