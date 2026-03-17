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
from proyectos.models import Proyecto
from .models import Ubicacion, UbicacionImagen
from .forms import UbicacionForm, UbicacionContenidoForm

logger = logging.getLogger(__name__)

N8N_WEBHOOK_UBICACION_URL = 'https://n8n.magoreal.com/webhook/ubicacion'




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
                    'indicaciones': indicaciones,
                    'pasos_totales': len(steps)
                }
    except Exception as e:
        print(f"Error al obtener indicaciones: {e}")
    
    return None


def crear_imagen_mapa(ubicacion_instance, google_maps_api_key=None):
    """
    Descarga y guarda la imagen del mapa desde Google Static Maps API
    También obtiene las indicaciones de cómo llegar desde el centro de la ciudad
    Retorna las indicaciones formateadas (pero NO las guarda en el contenido)
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
        
        # Obtener indicaciones de cómo llegar desde el centro de la ciudad
        indicaciones_texto = ""
        indicaciones_dict = None
        if ubicacion_instance.ciudad:
            try:
                # Obtener coordenadas del centro de la ciudad usando Geocoding API
                geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
                geocoding_params = {
                    'address': ubicacion_instance.ciudad,
                    'key': google_maps_api_key
                }
                geocoding_response = requests.get(geocoding_url, params=geocoding_params, timeout=10)
                geocoding_data = geocoding_response.json()
                
                if geocoding_data['status'] == 'OK' and geocoding_data['results']:
                    centro_ciudad = geocoding_data['results'][0]['geometry']['location']
                    centro_lat = centro_ciudad['lat']
                    centro_lon = centro_ciudad['lng']
                    
                    # Obtener indicaciones desde el centro de la ciudad hasta la ubicación
                    indicaciones_dict = obtener_indicaciones_ruta(
                        centro_lat, centro_lon,
                        latitud, longitud,
                        google_maps_api_key
                    )
                    
                    if indicaciones_dict:
                        # Formatear indicaciones en markdown (solo para enviar al webhook, NO se guardan en contenido)
                        indicaciones_texto = f"\n\n## Cómo Llegar\n\n"
                        indicaciones_texto += f"**Distancia total:** {indicaciones_dict['distancia_total']}\n\n"
                        indicaciones_texto += f"**Tiempo estimado:** {indicaciones_dict['duracion_total']}\n\n"
                        indicaciones_texto += f"**Indicaciones:**\n\n"
                        
                        for i, paso in enumerate(indicaciones_dict['indicaciones'][:10], 1):  # Primeros 10 pasos
                            indicaciones_texto += f"{i}. {paso['instruccion']} ({paso['distancia']})\n"
                        
                        # NO guardar las indicaciones en el contenido
                        # Solo se enviarán al webhook, el contenido final será reemplazado por la respuesta de la IA
                        logger.info(f"Indicaciones obtenidas para enviar al webhook: {len(indicaciones_texto)} caracteres")
            except Exception as e:
                logger.error(f"Error al obtener indicaciones: {e}")
                # Continuar sin indicaciones si hay error
        
        # Eliminar archivo temporal
        if os.path.exists(mapa_imagen_path):
            os.remove(mapa_imagen_path)
        
        # Retornar las indicaciones formateadas para enviarlas al webhook
        return indicaciones_texto
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


def enviar_a_n8n_ubicacion(ubicacion_instance, google_maps_api_key=None, indicaciones=None):
    """
    Envía los datos de la ubicación al webhook de n8n para generar contenido con IA
    Args:
        ubicacion_instance: Instancia del modelo Ubicacion
        google_maps_api_key: API key de Google Maps (opcional)
        indicaciones: Texto de indicaciones formateado en markdown (opcional)
    """
    try:
        # Preparar payload con toda la información disponible
        contenido_actual = ubicacion_instance.contenido or ''
        
        payload = {
            'nombre': ubicacion_instance.nombre,
            'descripcion': ubicacion_instance.descripcion or '',
            'latitud': float(ubicacion_instance.latitud) if ubicacion_instance.latitud else None,
            'longitud': float(ubicacion_instance.longitud) if ubicacion_instance.longitud else None,
            'ciudad': ubicacion_instance.ciudad or '',
            'contenido_actual': contenido_actual,
            'proyecto_nombre': ubicacion_instance.proyecto.nombre if ubicacion_instance.proyecto else '',
            'proyecto_solicitante': ubicacion_instance.proyecto.solicitante if ubicacion_instance.proyecto else '',
            'proyecto_ubicacion': ubicacion_instance.proyecto.ubicacion if ubicacion_instance.proyecto else '',
        }
        
        # Agregar indicaciones al payload si están disponibles (pasadas como parámetro)
        if indicaciones and indicaciones.strip():
            payload['indicaciones'] = indicaciones.strip()
            payload['tiene_indicaciones'] = True
            logger.info(f"Indicaciones incluidas en payload para webhook: {len(indicaciones)} caracteres")
        else:
            payload['tiene_indicaciones'] = False
        
        logger.info(f"Enviando datos de ubicación a n8n webhook: {N8N_WEBHOOK_UBICACION_URL}")
        logger.debug(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        # Enviar POST request al webhook de n8n
        response = requests.post(
            N8N_WEBHOOK_UBICACION_URL,
            json=payload,
            headers={
                'Content-Type': 'application/json'
            },
            timeout=60  # Timeout de 60 segundos
        )
        
        # Verificar si la respuesta fue exitosa
        response.raise_for_status()
        
        # Procesar la respuesta JSON
        response_data = None
        try:
            response_data = response.json()
            logger.info(f"Respuesta recibida de n8n webhook - Status: {response.status_code}")
            logger.debug(f"Respuesta JSON: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError as e:
            logger.warning(f"Respuesta no es JSON válido: {str(e)}")
            response_data = {'text': response.text, 'status_code': response.status_code}
        
        # Extraer el markdown generado por la IA
        markdown_generado = None
        
        # Intentar diferentes formatos de respuesta (similar a como se hace en n8n/views.py)
        # Formato esperado: [{"output": "markdown..."}]
        if isinstance(response_data, list) and len(response_data) > 0:
            first_item = response_data[0]
            if isinstance(first_item, dict):
                # Prioridad: output > pliego > contenido > markdown > text
                if 'output' in first_item:
                    markdown_generado = first_item['output']
                    logger.info(f"Markdown encontrado en formato array[0].output: {len(markdown_generado) if markdown_generado else 0} caracteres")
                elif 'pliego' in first_item:
                    markdown_generado = first_item['pliego']
                    logger.info(f"Markdown encontrado en formato array[0].pliego: {len(markdown_generado) if markdown_generado else 0} caracteres")
                elif 'contenido' in first_item:
                    markdown_generado = first_item['contenido']
                    logger.info(f"Markdown encontrado en formato array[0].contenido: {len(markdown_generado) if markdown_generado else 0} caracteres")
                elif 'markdown' in first_item:
                    markdown_generado = first_item['markdown']
                    logger.info(f"Markdown encontrado en formato array[0].markdown: {len(markdown_generado) if markdown_generado else 0} caracteres")
                elif 'text' in first_item:
                    markdown_generado = first_item['text']
                    logger.info(f"Markdown encontrado en formato array[0].text: {len(markdown_generado) if markdown_generado else 0} caracteres")
        
        elif isinstance(response_data, dict):
            # Buscar en diferentes campos posibles (formato objeto directo)
            if 'output' in response_data:
                markdown_generado = response_data['output']
                logger.info(f"Markdown encontrado en campo 'output': {len(markdown_generado) if markdown_generado else 0} caracteres")
            elif 'pliego' in response_data:
                markdown_generado = response_data['pliego']
                logger.info(f"Markdown encontrado en campo 'pliego': {len(markdown_generado) if markdown_generado else 0} caracteres")
            elif 'contenido' in response_data:
                markdown_generado = response_data['contenido']
                logger.info(f"Markdown encontrado en campo 'contenido': {len(markdown_generado) if markdown_generado else 0} caracteres")
            elif 'markdown' in response_data:
                markdown_generado = response_data['markdown']
                logger.info(f"Markdown encontrado en campo 'markdown': {len(markdown_generado) if markdown_generado else 0} caracteres")
            elif 'text' in response_data:
                markdown_generado = response_data['text']
                logger.info(f"Markdown encontrado en campo 'text': {len(markdown_generado) if markdown_generado else 0} caracteres")
        
        # Si se encontró markdown generado, guardarlo en el contenido
        if markdown_generado and isinstance(markdown_generado, str) and markdown_generado.strip():
            # Extraer solo el contenido desde "UBICACIÓN DEL SITIO" en adelante
            contenido_final = markdown_generado.strip()
            
            # Buscar el inicio del contenido que queremos guardar
            marcador_inicio = "UBICACIÓN DEL SITIO"
            if marcador_inicio in contenido_final:
                # Encontrar la posición donde comienza "UBICACIÓN DEL SITIO"
                indice_inicio = contenido_final.find(marcador_inicio)
                # Extraer desde ese punto en adelante
                contenido_final = contenido_final[indice_inicio:].strip()
                logger.info(f"Contenido extraído desde '{marcador_inicio}': {len(contenido_final)} caracteres")
            else:
                # Si no se encuentra el marcador, usar todo el contenido
                logger.warning(f"No se encontró el marcador '{marcador_inicio}' en el contenido generado. Usando todo el contenido.")
            
            # Reemplazar completamente el contenido con el generado por IA (sin las indicaciones previas)
            ubicacion_instance.contenido = contenido_final
            logger.info(f"Contenido markdown generado guardado: {len(ubicacion_instance.contenido)} caracteres")
            
            return True
        else:
            logger.warning(f"No se encontró markdown en la respuesta del webhook. Tipo de respuesta: {type(response_data)}")
            if isinstance(response_data, list):
                logger.warning(f"Array con {len(response_data)} elementos")
            return False
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout al enviar a {N8N_WEBHOOK_UBICACION_URL}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al comunicarse con el webhook {N8N_WEBHOOK_UBICACION_URL}: {str(e)}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Error inesperado al procesar respuesta del webhook: {str(e)}", exc_info=True)
        return False


@login_required
def crear_ubicacion_view(request, proyecto_id):
    """
    Vista para crear una nueva ubicación
    """
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, activo=True)
    
    if proyecto.creado_por != request.user:
        messages.error(request, 'Solo puedes crear ubicaciones en tus propios proyectos.')
        return redirect('proyectos:proyecto_detalle', proyecto.id)
    
    if request.method == 'POST':
        form = UbicacionForm(request.POST)
        if form.is_valid():
            ubicacion = form.save(commit=False)
            ubicacion.proyecto = proyecto

            if ubicacion.latitud and ubicacion.longitud:
                try:
                    ubicacion.save()
                    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
                    indicaciones_texto = crear_imagen_mapa(ubicacion, google_maps_api_key=api_key)
                    ubicacion.save()
                    try:
                        contenido_generado = enviar_a_n8n_ubicacion(ubicacion, google_maps_api_key=api_key, indicaciones=indicaciones_texto)
                        if contenido_generado:
                            ubicacion.save()
                            messages.success(request, f'Ubicación "{ubicacion.nombre}" creada. Mapa y contenido generados automáticamente.')
                        else:
                            messages.success(request, f'Ubicación "{ubicacion.nombre}" creada. Mapa generado automáticamente.')
                    except Exception as e:
                        logger.error(f"Error al enviar a n8n: {str(e)}", exc_info=True)
                        messages.success(request, f'Ubicación "{ubicacion.nombre}" creada. Mapa generado, pero hubo un error al generar el contenido con IA.')
                except ValueError:
                    ubicacion.save()
                    messages.warning(request, f'Ubicación "{ubicacion.nombre}" creada. Configure GOOGLE_MAPS_API_KEY para generar el mapa automáticamente.')
                except Exception as e:
                    ubicacion.save()
                    messages.warning(request, f'Ubicación "{ubicacion.nombre}" creada, pero hubo un error al generar el mapa: {str(e)}')
            else:
                ubicacion.save()
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
    
    if proyecto.creado_por != request.user:
        messages.error(request, 'Solo puedes editar ubicaciones de tus proyectos.')
        return redirect('proyectos:proyecto_detalle', proyecto.id)
    
    if request.method == 'POST':
        form = UbicacionForm(request.POST, instance=ubicacion)
        if form.is_valid():
            form.save()
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
def editar_contenido_ubicacion_view(request, ubicacion_id):
    """
    Vista para editar el contenido markdown de una ubicación
    """
    ubicacion = get_object_or_404(Ubicacion, id=ubicacion_id, proyecto__activo=True)
    proyecto = ubicacion.proyecto

    if proyecto.creado_por != request.user:
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
    
    if proyecto.creado_por != request.user:
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
    if not (ubicacion.proyecto.publico or ubicacion.proyecto.creado_por == request.user):
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
    
    # Verificar que el usuario es propietario del proyecto
    if ubicacion.proyecto.creado_por != request.user:
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
    
    # Verificar que el usuario es propietario del proyecto
    if ubicacion.proyecto.creado_por != request.user:
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
    
    # Verificar que el usuario es propietario del proyecto
    if ubicacion.proyecto.creado_por != request.user:
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
    if not (ubicacion.proyecto.publico or ubicacion.proyecto.creado_por == request.user):
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
