import requests
import math
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
import os
from django.conf import settings
from django.core.files import File
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from markdown import markdown
from bs4 import BeautifulSoup


def calcular_distancia_haversine(lat1, lon1, lat2, lon2):
    """Calcula la distancia entre dos puntos usando la fórmula de Haversine"""
    R = 6371  # Radio de la Tierra en kilómetros
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def obtener_coordenadas_centro_ciudad(ciudad, google_maps_api_key):
    """Obtiene las coordenadas del centro de una ciudad usando Google Geocoding API"""
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': ciudad,
            'key': google_maps_api_key
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    except Exception:
        pass
    return None, None


def obtener_indicaciones_ruta(origen_lat, origen_lon, destino_lat, destino_lon, google_maps_api_key):
    """
    Obtiene las indicaciones de ruta desde un origen hasta un destino usando Google Directions API
    Retorna un resumen de las principales vías y direcciones
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
                
                # Extraer las principales vías y direcciones
                vias_principales = []
                direcciones_resumidas = []
                
                # Procesar los primeros pasos importantes (hasta 5 pasos principales)
                pasos_importantes = []
                for i, step in enumerate(steps[:15]):  # Revisar primeros 15 pasos
                    html_instructions = step.get('html_instructions', '')
                    distance = step.get('distance', {}).get('value', 0)  # en metros
                    
                    # Solo considerar pasos significativos (más de 100m o que mencionen vías)
                    if distance > 100 or any(palabra in html_instructions.lower() for palabra in 
                                           ['avenida', 'calle', 'ruta', 'carretera', 'boulevard', 'av.', 'av']):
                        pasos_importantes.append({
                            'instructions': html_instructions,
                            'distance': distance,
                            'index': i
                        })
                        if len(pasos_importantes) >= 5:
                            break
                
                # Extraer nombres de vías de las instrucciones
                for paso in pasos_importantes:
                    # Limpiar HTML de las instrucciones
                    texto_limpio = re.sub(r'<[^>]+>', '', paso['instructions'])
                    
                    # Buscar nombres de vías (patrones comunes)
                    # Buscar después de palabras como "por", "hacia", "en", "siga"
                    patrones_via = [
                        r'(?:por|hacia|en|siga|tome|gire en|continúe por)\s+([A-ZÁÉÍÓÚÑ][^,\.]+?)(?:,|\.|$)',
                        r'(avenida|av\.?|calle|ruta|carretera|boulevard|blvd)\s+([A-ZÁÉÍÓÚÑ][^,\.]+?)(?:,|\.|$)',
                    ]
                    
                    for patron in patrones_via:
                        matches = re.findall(patron, texto_limpio, re.IGNORECASE)
                        for match in matches:
                            if isinstance(match, tuple):
                                via = ' '.join(m for m in match if m).strip()
                            else:
                                via = match.strip()
                            
                            # Filtrar Plus Codes y códigos cortos
                            if via and len(via) > 5 and '+' not in via and via not in vias_principales:
                                # Verificar que no sea solo números o códigos
                                if not (via.replace(' ', '').isdigit() or len(via) <= 8):
                                    vias_principales.append(via)
                
                # Si no encontramos vías específicas, usar las instrucciones resumidas
                if not vias_principales and pasos_importantes:
                    # Tomar las primeras 2-3 instrucciones principales
                    for paso in pasos_importantes[:3]:
                        texto_limpio = re.sub(r'<[^>]+>', '', paso['instructions'])
                        # Limpiar y acortar
                        texto_limpio = texto_limpio.split('.')[0].strip()
                        if texto_limpio and len(texto_limpio) > 10:
                            direcciones_resumidas.append(texto_limpio)
                
                return {
                    'vias': vias_principales,
                    'instrucciones': direcciones_resumidas,
                    'distancia_total': leg.get('distance', {}).get('text', ''),
                    'duracion': leg.get('duration', {}).get('text', '')
                }
    except Exception as e:
        print(f"Error al obtener indicaciones: {e}")
        pass
    return {}


def generar_descripciones_con_gpt(nombre_sitio, latitud, longitud, ciudad, nombre_zona, 
                                   distancia_centro, vias_acceso, indicaciones_ruta, direccion_completa,
                                   descripcion_usuario=None):
    """
    Genera descripciones mejoradas de acceso y técnica usando GPT
    """
    try:
        # Verificar que la API key esté configurada
        api_key = os.getenv('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', '')
        if not api_key:
            raise ValueError("OPENAI_API_KEY no configurada")
        
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
        )
        
        # Preparar información de vías
        vias_texto = ""
        if vias_acceso:
            vias_texto = ", ".join(vias_acceso[:5])  # Máximo 5 vías
        elif indicaciones_ruta.get('vias'):
            vias_texto = ", ".join(indicaciones_ruta.get('vias', [])[:5])
        
        # Preparar información de distancia
        distancia_texto = ""
        if distancia_centro:
            distancia_texto = f"{distancia_centro:.2f} km"
        
        # Preparar información de indicaciones
        instrucciones_texto = ""
        if indicaciones_ruta.get('instrucciones'):
            instrucciones_texto = " ".join(indicaciones_ruta.get('instrucciones', [])[:3])
        
        # Preparar información de descripción del usuario
        descripcion_usuario_texto = ""
        if descripcion_usuario and descripcion_usuario.strip():
            descripcion_usuario_texto = descripcion_usuario.strip()
        
        prompt_template = ChatPromptTemplate.from_template("""
Eres un experto en redacción técnica de documentos de ingeniería y construcción. Tu tarea es generar dos descripciones profesionales, objetivas y completamente factuales para un documento de ubicación de sitio que será entregado a empresas de servicios o construcción.

## Información del sitio:
- **Nombre del sitio**: {nombre_sitio}
- **Coordenadas**: Latitud {latitud:.6f}°, Longitud {longitud:.6f}°
- **Ciudad**: {ciudad}
- **Zona/Área**: {nombre_zona}
{distancia_texto_linea}{vias_texto_linea}{direccion_completa_linea}{instrucciones_texto_linea}{descripcion_usuario_seccion}

## Tarea:
Genera DOS descripciones profesionales, objetivas y completamente factuales en español. 

**CONSIDERACIÓN DE LA DESCRIPCIÓN DEL USUARIO:**
Si hay una descripción proporcionada por el usuario en la sección de información del sitio, debes:
- Usarla como información base y contexto principal
- Incorporar todos los datos relevantes de la descripción del usuario
- Expandir y estructurar la información de manera profesional y técnica
- Mantener el estilo neutral y factual requerido
- No agregar información que contradiga lo que el usuario ha proporcionado

**REGLAS ESTRICTAS DE REDACCIÓN:**
- NO uses calificativos positivos o negativos (como "favorable", "adecuado", "excelente", "conveniente", "óptimo", "estratégicamente", "apto", "buenas condiciones", etc.)
- NO evalúes ni juzgues las condiciones del sitio
- NO menciones si es apto o no para ningún propósito
- NO uses frases como "ofrece", "permite", "facilita", "cuenta con condiciones favorables"
- SOLO describe hechos concretos: ubicación, distancias, rutas, características físicas observables
- El documento debe ser puramente descriptivo y técnico, presentando información factual sin evaluaciones
- **IMPORTANTE**: Si no existe información sobre algún aspecto, NO lo menciones en absoluto. No uses frases como "no disponible", "no especificado", "no calculada", etc. Solo incluye información que realmente existe y está disponible

### 1. Descripción de Acceso:
Redacta un párrafo técnico y completamente factual que describa la ubicación del sitio y las rutas de acceso principales desde el centro de la ciudad. Debe incluir SOLO:
- Ubicación específica (zona, área, relación geográfica con la ciudad)
- Distancia al centro (en kilómetros) - solo si está disponible
- Rutas principales de acceso mencionando las avenidas y calles específicas si están disponibles
- Información factual sobre conectividad (qué rutas existen, no si son buenas o malas)
- Estilo profesional, descriptivo y completamente neutral, solo hechos
- Si hay información en la descripción proporcionada por el usuario relacionada con acceso o ubicación, incorpórala de manera objetiva

Ejemplo de estilo correcto (completamente factual):
"El sitio se encuentra ubicado en el norte de Santa Cruz de la Sierra, dentro del Parque Industrial Latinoamericano. El acceso desde el centro de la ciudad se realiza mediante Avenida Cristo Redentor, conectando con el Tercer Anillo Externo, luego hacia el norte por Avenida Banzer hasta Avenida Mutualista. Esta ruta tiene aproximadamente 7 a 8 kilómetros hasta el sitio específico. La distancia total desde el sitio hasta el centro de la ciudad de Santa Cruz de la Sierra, Bolivia, se estima entre 10 y 12 kilómetros, dependiendo de la ruta exacta y las condiciones de tráfico."

### 2. Descripción Técnica del Sitio:
Redacta un párrafo técnico que describa las características técnicas y topográficas del emplazamiento de manera completamente factual. Debe incluir SOLO:
- Georreferenciación precisa (coordenadas)
- Características topográficas observables del área
- Descripción del terreno (tipo de suelo, pendientes, etc.) sin evaluar si es bueno o malo
- Información sobre servicios e infraestructura existente (qué hay, no si es adecuado)
- Datos técnicos medibles y observables
- Estilo académico, profesional y completamente neutral, solo descripción de hechos observables
- **IMPORTANTE**: Si hay una descripción proporcionada por el usuario, debes incorporarla y expandirla de manera objetiva en esta descripción técnica, manteniendo el estilo neutral y factual requerido
{descripcion_usuario_instruccion}

## Formato de respuesta:
Responde ÚNICAMENTE con un JSON válido con esta estructura exacta:
{{
    "descripcion_acceso": "texto de la descripción de acceso aquí",
    "descripcion_tecnica": "texto de la descripción técnica aquí"
}}

No incluyas explicaciones adicionales, solo el JSON.
""")
        
        chain = prompt_template | llm | StrOutputParser()
        
        # Construir sección de descripción del usuario si existe
        descripcion_usuario_seccion = ""
        descripcion_usuario_instruccion = ""
        if descripcion_usuario_texto:
            descripcion_usuario_seccion = f"- **Descripción proporcionada por el usuario**: {descripcion_usuario_texto}"
            descripcion_usuario_instruccion = "\n\n**IMPORTANTE**: Debes incorporar y expandir la información proporcionada por el usuario en las descripciones, especialmente en la descripción técnica. Usa la descripción del usuario como base y contexto, pero mantén el estilo profesional, técnico y completamente neutral requerido. NO agregues calificativos, juicios de valor, evaluaciones sobre condiciones, ni menciones sobre si es apto o no. Solo describe hechos concretos y observables."
        
        # Construir líneas de información solo si existen
        distancia_texto_linea = f"- **Distancia al centro de la ciudad**: {distancia_texto}\n" if distancia_texto else ""
        vias_texto_linea = f"- **Vías de acceso principales**: {vias_texto}\n" if vias_texto else ""
        direccion_completa_linea = f"- **Dirección completa**: {direccion_completa}\n" if direccion_completa else ""
        instrucciones_texto_linea = f"- **Instrucciones de ruta**: {instrucciones_texto}\n" if instrucciones_texto else ""
        
        # Preparar variables para el prompt
        variables_prompt = {
            "nombre_sitio": nombre_sitio,
            "latitud": latitud,
            "longitud": longitud,
            "ciudad": ciudad,
            "nombre_zona": nombre_zona,
            "distancia_texto_linea": distancia_texto_linea,
            "vias_texto_linea": vias_texto_linea,
            "direccion_completa_linea": direccion_completa_linea,
            "instrucciones_texto_linea": instrucciones_texto_linea,
            "descripcion_usuario_seccion": descripcion_usuario_seccion,
            "descripcion_usuario_instruccion": descripcion_usuario_instruccion
        }
        
        response = chain.invoke(variables_prompt)
        
        # Extraer JSON de la respuesta (puede venir con markdown)
        import json
        # Limpiar markdown si está presente
        response_limpia = response.strip()
        if response_limpia.startswith("```json"):
            response_limpia = response_limpia[7:]
        if response_limpia.startswith("```"):
            response_limpia = response_limpia[3:]
        if response_limpia.endswith("```"):
            response_limpia = response_limpia[:-3]
        response_limpia = response_limpia.strip()
        
        resultado = json.loads(response_limpia)
        return resultado
        
    except Exception as e:
        print(f"Error en generar_descripciones_con_gpt: {e}")
        raise


def obtener_info_geocoding(lat, lon, google_maps_api_key):
    """Obtiene información de geocoding inverso usando Google API"""
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'latlng': f"{lat},{lon}",
            'key': google_maps_api_key,
            'language': 'es'
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data['status'] == 'OK' and data['results']:
            result = data['results'][0]
            # Extraer componentes de manera más completa
            components = {}
            for comp in result.get('address_components', []):
                for comp_type in comp.get('types', []):
                    if comp_type not in components:
                        components[comp_type] = comp['long_name']
            
            # Extraer información de rutas/calles/avenidas
            ruta = components.get('route', '')
            calle_numero = components.get('street_number', '')
            direccion_completa = result.get('formatted_address', '')
            
            # Construir información de vías de acceso (avenidas, calles, rutas)
            vias_acceso = []
            
            # Función auxiliar para verificar si es un Plus Code o código no válido
            def es_via_valida(texto):
                if not texto or len(texto.strip()) < 3:
                    return False
                texto_limpio = texto.strip()
                # Filtrar Plus Codes (formato: letras/números cortos con +)
                if '+' in texto_limpio and len(texto_limpio) <= 12:
                    return False
                # Filtrar códigos muy cortos que parecen Plus Codes (ej: "6VF4+2G4", "6VF4")
                if len(texto_limpio) <= 8 and texto_limpio.replace(' ', '').replace('-', '').replace('+', '').isalnum():
                    return False
                # Filtrar solo números
                if texto_limpio.replace(' ', '').replace('#', '').isdigit():
                    return False
                return True
            
            # Buscar en todos los componentes de dirección
            tipos_via = ['route', 'street_address', 'premise']
            for tipo_via in tipos_via:
                if components.get(tipo_via):
                    via_valor = components.get(tipo_via, '')
                    if es_via_valida(via_valor) and via_valor not in vias_acceso:
                        vias_acceso.append(via_valor)
            
            # También buscar en los componentes de address_components directamente
            for comp in result.get('address_components', []):
                tipos = comp.get('types', [])
                if 'route' in tipos or 'street_address' in tipos:
                    nombre_via = comp.get('long_name', '')
                    if es_via_valida(nombre_via) and nombre_via not in vias_acceso:
                        vias_acceso.append(nombre_via)
            
            # Buscar en la dirección completa si no encontramos vías válidas
            if not vias_acceso and direccion_completa:
                # Dividir la dirección y buscar partes que parezcan calles/avenidas
                partes = direccion_completa.split(',')
                for parte in partes:
                    parte_limpia = parte.strip()
                    # Filtrar Plus Codes y códigos cortos
                    if es_via_valida(parte_limpia):
                        # Verificar que contenga palabras comunes de direcciones o sea suficientemente larga
                        palabras_direccion = ['avenida', 'av.', 'av', 'calle', 'ruta', 'carretera', 
                                             'boulevard', 'blvd', 'pasaje', 'camino', 'vía', 'street', 
                                             'road', 'avenue', 'way', 'drive']
                        if (any(palabra in parte_limpia.lower() for palabra in palabras_direccion) or
                            len(parte_limpia) > 15):
                            if parte_limpia not in vias_acceso:
                                vias_acceso.append(parte_limpia)
                                if len(vias_acceso) >= 3:  # Máximo 3 vías
                                    break
            
            return {
                'direccion': direccion_completa,
                'barrio': components.get('sublocality', components.get('neighborhood', '')),
                'distrito': components.get('administrative_area_level_2', ''),
                'provincia': components.get('administrative_area_level_2', ''),
                'ciudad': components.get('locality', components.get('administrative_area_level_1', '')),
                'ruta': ruta,
                'calle_numero': calle_numero,
                'vias_acceso': vias_acceso,  # Lista de vías de acceso encontradas
                'pais': components.get('country', ''),
            }
    except Exception:
        pass
    return {}


def generar_ubicacion_pdf(ubicacion_instance, google_maps_api_key=None):
    """
    Genera un PDF completo con información de ubicación del sitio
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
    nombre_sitio = ubicacion_instance.nombre
    
    # Crear directorio temporal si no existe
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'ubicaciones', 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    output_path = os.path.join(temp_dir, f'ubicacion_{ubicacion_instance.id}.pdf')
    
    # Inferir zoom óptimo (entre 15 y 18)
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
        response.raise_for_status()
        mapa_imagen_path = os.path.join(os.path.dirname(output_path), "mapa_sitio.png")
        with open(mapa_imagen_path, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        raise Exception(f"Error al descargar el mapa: {str(e)}")
    
    # Obtener información de geocoding inverso (basado en coordenadas)
    info_geo = obtener_info_geocoding(latitud, longitud, google_maps_api_key)
    
    # Determinar la ciudad a usar: primero la detectada por Google, luego la ingresada manualmente
    ciudad_detectada = info_geo.get('ciudad', '')
    ciudad_manual = ubicacion_instance.ciudad or ''
    
    # Usar la ciudad detectada si está disponible, sino usar la manual, sino usar un valor por defecto
    if ciudad_detectada:
        ciudad = ciudad_detectada
        ciudad_para_calculo = ciudad_detectada
    elif ciudad_manual:
        ciudad = ciudad_manual
        ciudad_para_calculo = ciudad_manual
    else:
        ciudad = "Ciudad no especificada"
        ciudad_para_calculo = None
    
    # Obtener coordenadas del centro de la ciudad (usando la ciudad determinada)
    centro_lat, centro_lon = None, None
    if ciudad_para_calculo:
        centro_lat, centro_lon = obtener_coordenadas_centro_ciudad(ciudad_para_calculo, google_maps_api_key)
    
    # Calcular distancia al centro si se obtuvieron coordenadas
    distancia_centro = None
    if centro_lat and centro_lon:
        distancia_centro = calcular_distancia_haversine(latitud, longitud, centro_lat, centro_lon)
    
    # Obtener indicaciones de ruta desde el centro de la ciudad hasta la ubicación
    indicaciones_ruta = {}
    if centro_lat and centro_lon:
        indicaciones_ruta = obtener_indicaciones_ruta(
            centro_lat, centro_lon, latitud, longitud, google_maps_api_key
        )
    
    # Inferir nombre de zona (priorizar información de geocoding)
    nombre_zona = info_geo.get('barrio', '') or info_geo.get('distrito', '') or info_geo.get('provincia', '')
    if not nombre_zona:
        nombre_zona = f"Zona de {ciudad}" if ciudad else "Zona no especificada"
    
    # Extraer información de rutas/calles/avenidas de Google Maps
    vias_acceso = info_geo.get('vias_acceso', [])
    ruta = info_geo.get('ruta', '')
    direccion_completa = info_geo.get('direccion', '')
    
    # Generar descripción de acceso mejorada usando información de Google Maps
    partes_acceso = []
    
    # Agregar ubicación específica
    if nombre_zona:
        partes_acceso.append(nombre_zona)
    
    # Agregar distancia al centro si está disponible
    if distancia_centro:
        distancia_texto = f"{distancia_centro:.2f} km"
        partes_acceso.append(f"a {distancia_texto} del centro de {ciudad}")
    
    # Construir texto base de ubicación
    if partes_acceso:
        texto_ubicacion = f"El sitio está localizado en {', '.join(partes_acceso)}."
    else:
        texto_ubicacion = f"El sitio está localizado en {ciudad}."
    
    # Agregar información de acceso específica usando indicaciones de Google Maps
    texto_acceso = ""
    
    # Priorizar: usar vías de las indicaciones de ruta (Directions API)
    if indicaciones_ruta.get('vias'):
        vias_directions = indicaciones_ruta.get('vias', [])
        # Filtrar y limitar a las más relevantes (máximo 3)
        vias_filtradas = [v for v in vias_directions[:3] if len(v) > 5]
        if vias_filtradas:
            texto_acceso = f"Acceso por {', '.join(vias_filtradas)}"
    
    # Si no hay vías de Directions API, usar las encontradas en geocoding
    if not texto_acceso:
        if vias_acceso:
            # Unir múltiples vías si hay más de una
            vias_texto = ", ".join(vias_acceso[:3])  # Máximo 3 vías
            texto_acceso = f"Acceso por {vias_texto}"
        elif ruta:
            # Verificar que la ruta no sea un Plus Code
            ruta_limpia = ruta.strip()
            # Filtrar Plus Codes (códigos cortos con + o muy cortos)
            if len(ruta_limpia) > 10 or ('+' not in ruta_limpia and not (len(ruta_limpia) <= 8 and ruta_limpia.replace(' ', '').isalnum())):
                texto_acceso = f"Acceso por {ruta_limpia}"
    
    # Si aún no hay información específica, intentar extraer de la dirección completa
    if not texto_acceso and direccion_completa:
        # Dividir la dirección y buscar partes que parezcan calles/avenidas
        partes_direccion = direccion_completa.split(',')
        vias_encontradas = []
        for parte in partes_direccion:
            parte_limpia = parte.strip()
            # Filtrar Plus Codes y códigos cortos
            if parte_limpia and len(parte_limpia) > 10:
                # Verificar que no sea solo números o códigos
                if not (parte_limpia.replace(' ', '').replace('#', '').isdigit() or 
                        (len(parte_limpia) <= 12 and '+' in parte_limpia)):
                    # Verificar que contenga palabras comunes de direcciones o que no sea solo la ciudad
                    palabras_direccion = ['avenida', 'av.', 'av', 'calle', 'ruta', 'carretera', 
                                         'boulevard', 'blvd', 'pasaje', 'camino', 'vía', 'street', 'road']
                    if (any(palabra in parte_limpia.lower() for palabra in palabras_direccion) or
                        (parte_limpia.lower() != ciudad.lower() and len(parte_limpia) > 15)):
                        vias_encontradas.append(parte_limpia)
                        if len(vias_encontradas) >= 2:  # Máximo 2 vías
                            break
        
        if vias_encontradas:
            texto_acceso = f"Acceso por {', '.join(vias_encontradas[:2])}"  # Máximo 2 vías
    
    # Si no hay información específica, usar texto genérico según distancia
    if not texto_acceso:
        if distancia_centro:
            if distancia_centro < 5:
                texto_acceso = "Acceso directo por vías principales"
            elif distancia_centro < 15:
                texto_acceso = "Acceso por vías principales del área metropolitana"
            else:
                texto_acceso = "Acceso por carreteras principales"
        else:
            texto_acceso = "Acceso por vías principales"
    
    # Usar contenido markdown si existe, sino generar uno con GPT
    contenido_markdown = ubicacion_instance.contenido.strip() if ubicacion_instance.contenido else None
    
    if not contenido_markdown:
        # Generar contenido markdown usando GPT
        try:
            descripciones_mejoradas = generar_descripciones_con_gpt(
                nombre_sitio=nombre_sitio,
                latitud=latitud,
                longitud=longitud,
                ciudad=ciudad,
                nombre_zona=nombre_zona,
                distancia_centro=distancia_centro,
                vias_acceso=vias_acceso if vias_acceso else indicaciones_ruta.get('vias', []),
                indicaciones_ruta=indicaciones_ruta,
                direccion_completa=direccion_completa,
                descripcion_usuario=ubicacion_instance.descripcion
            )
            descripcion_acceso = descripciones_mejoradas.get('descripcion_acceso', '')
            descripcion_tecnica = descripciones_mejoradas.get('descripcion_tecnica', '')
            
            # Generar contenido markdown estructurado con tabla e imagen
            # La tabla y la imagen se agregarán después de guardar la ubicación
            contenido_markdown = f"""{descripcion_tecnica}

## Descripción de Acceso

{descripcion_acceso}
"""
            # Guardar el contenido generado en la instancia (sin tabla e imagen aún)
            ubicacion_instance.contenido = contenido_markdown
            ubicacion_instance.save(update_fields=['contenido'])
        except Exception as e:
            print(f"Error al generar descripciones con GPT: {e}")
            # Usar descripciones básicas si falla GPT
            descripcion_acceso_temporal = f"{texto_ubicacion} {texto_acceso}."
            descripcion_tecnica = (
                f"El sitio {nombre_sitio} está georreferenciado en las coordenadas {latitud:.6f}°N, {longitud:.6f}°W, "
                f"ubicado en la zona de {nombre_zona}, {ciudad}. La localización presenta características topográficas "
                f"propias del área, con accesibilidad adecuada para el desarrollo de actividades técnicas y operativas. "
                f"El emplazamiento cuenta con condiciones favorables para la implementación de infraestructura, "
                f"considerando aspectos de conectividad, servicios básicos y normativas urbanas vigentes."
            )
            contenido_markdown = f"""{descripcion_tecnica}

## Descripción de Acceso

{descripcion_acceso_temporal}
"""
            ubicacion_instance.contenido = contenido_markdown
            ubicacion_instance.save(update_fields=['contenido'])
    
    # Crear PDF
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        alignment=TA_JUSTIFY,
        leading=14,
        spaceAfter=8
    )
    
    # Título principal (nivel 2)
    heading_style_2 = ParagraphStyle(
        'Heading2',
        parent=heading_style,
        fontSize=16,
        spaceAfter=12,
        spaceBefore=12
    )
    story.append(Paragraph("Ubicación del Sitio", heading_style_2))
    story.append(Spacer(1, 0.2*inch))
    
    # Convertir markdown a HTML y procesar para el PDF
    contenido_html = markdown(contenido_markdown, extensions=['extra', 'nl2br'])
    soup = BeautifulSoup(contenido_html, 'html.parser')
    
    # Función auxiliar para convertir HTML a formato ReportLab
    def html_to_reportlab(html_element):
        """Convierte un elemento HTML a formato ReportLab"""
        texto = ""
        for item in html_element.children:
            if isinstance(item, str):
                texto += item
            elif hasattr(item, 'name'):
                if item.name == 'strong' or item.name == 'b':
                    texto += f"<b>{item.get_text()}</b>"
                elif item.name == 'em' or item.name == 'i':
                    texto += f"<i>{item.get_text()}</i>"
                elif item.name == 'a':
                    texto += item.get_text()  # Solo el texto, sin el enlace
                elif item.name == 'br':
                    texto += "<br/>"
                else:
                    texto += item.get_text()
        return texto
    
    # Separar las secciones: encontrar "Descripción de Acceso" y separarla
    # También detectar tabla e imagen para procesarlas correctamente
    descripcion_acceso_contenido = []
    contenido_principal = []
    tabla_encontrada = None
    imagen_encontrada = None
    caption_imagen = None
    seccion_actual = contenido_principal
    en_seccion_acceso = False
    en_seccion_coordenadas = False
    en_seccion_mapa = False
    
    # Procesar el contenido HTML separando las secciones
    for element in soup.children:
        if hasattr(element, 'name') and element.name:
            # Detectar si estamos en la sección "Descripción de Acceso"
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                texto_titulo = element.get_text().strip()
                if 'Descripción de Acceso' in texto_titulo or 'descripción de acceso' in texto_titulo.lower():
                    en_seccion_acceso = True
                    en_seccion_coordenadas = False
                    en_seccion_mapa = False
                    seccion_actual = descripcion_acceso_contenido
                    continue  # No agregar el título
                elif 'Coordenadas' in texto_titulo or 'coordenadas' in texto_titulo.lower():
                    en_seccion_coordenadas = True
                    en_seccion_mapa = False
                    en_seccion_acceso = False
                    seccion_actual = contenido_principal
                    continue  # No agregar el título de coordenadas al contenido principal
                elif 'Mapa' in texto_titulo or 'mapa' in texto_titulo.lower():
                    en_seccion_mapa = True
                    en_seccion_coordenadas = False
                    en_seccion_acceso = False
                    seccion_actual = contenido_principal
                    continue  # No agregar el título del mapa al contenido principal
                elif 'Ubicación del Sitio' in texto_titulo or 'ubicación del sitio' in texto_titulo.lower():
                    # Ignorar el título "Ubicación del Sitio" ya que se agrega como título principal del PDF
                    continue
                else:
                    en_seccion_acceso = False
                    en_seccion_coordenadas = False
                    en_seccion_mapa = False
                    seccion_actual = contenido_principal
            
            # Detectar tablas (solo en sección de coordenadas)
            if element.name == 'table' and en_seccion_coordenadas:
                tabla_encontrada = element
                continue  # La tabla se procesará después
            
            # Detectar imágenes (solo en sección de mapa)
            if element.name == 'img' and en_seccion_mapa:
                imagen_encontrada = element
                continue  # La imagen se procesará después
            
            # Detectar párrafos que contengan imágenes (markdown images)
            if element.name == 'p' and en_seccion_mapa:
                img_in_p = element.find('img')
                if img_in_p:
                    imagen_encontrada = img_in_p
                    # Buscar el siguiente párrafo que pueda ser el caption
                    next_p = element.find_next_sibling('p')
                    if next_p and ('Figura' in next_p.get_text() or 'figura' in next_p.get_text()):
                        caption_imagen = next_p
                    continue
            
            # Agregar el elemento a la sección correspondiente
            if not en_seccion_coordenadas and not en_seccion_mapa:
                seccion_actual.append(element)
    
    # Procesar contenido principal (sin la descripción de acceso)
    for element in contenido_principal:
        if hasattr(element, 'name') and element.name:
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Títulos
                nivel = int(element.name[1]) if len(element.name) > 1 else 1
                estilo_titulo = ParagraphStyle(
                    f'Heading{nivel}',
                    parent=heading_style,
                    fontSize=14 - (nivel - 2) * 2 if nivel >= 2 else 14,
                    spaceAfter=8,
                    spaceBefore=12 if nivel == 2 else 8
                )
                story.append(Paragraph(element.get_text(), estilo_titulo))
            elif element.name == 'p':
                # Párrafos con formato HTML
                texto_parrafo = html_to_reportlab(element)
                if texto_parrafo.strip():
                    story.append(Paragraph(texto_parrafo, body_style))
            elif element.name in ['ul', 'ol']:
                # Listas
                for li in element.find_all('li', recursive=False):
                    texto_item = html_to_reportlab(li)
                    # Agregar viñeta o número según el tipo de lista
                    if element.name == 'ul':
                        texto_item = f"• {texto_item}"
                    story.append(Paragraph(texto_item, body_style))
                    story.append(Spacer(1, 0.1*inch))
            elif element.name == 'br':
                story.append(Spacer(1, 0.1*inch))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Procesar tabla si está en el markdown, sino usar la tabla por defecto
    if tabla_encontrada:
        # Extraer datos de la tabla HTML del markdown
        filas = tabla_encontrada.find_all('tr')
        coordenadas_data = []
        for fila in filas[1:]:  # Saltar el encabezado
            celdas = fila.find_all(['td', 'th'])
            if len(celdas) >= 2:
                coordenadas_data.append([celdas[0].get_text().strip(), celdas[1].get_text().strip()])
        
        if coordenadas_data:
            tabla_coordenadas = Table(coordenadas_data, colWidths=[2*inch, 4*inch])
            tabla_coordenadas.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ]))
            story.append(tabla_coordenadas)
            story.append(Spacer(1, 0.3*inch))
    
    # Si no hay tabla en el markdown, usar la tabla por defecto
    if not tabla_encontrada:
        coordenadas_data = [
            ['Latitud', f'{latitud:.6f}°'],
            ['Longitud', f'{longitud:.6f}°'],
        ]
        
        if distancia_centro:
            coordenadas_data.append(['Distancia al centro', f'{distancia_centro:.2f} km'])
        
        tabla_coordenadas = Table(coordenadas_data, colWidths=[2*inch, 4*inch])
        tabla_coordenadas.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ]))
        story.append(tabla_coordenadas)
        story.append(Spacer(1, 0.3*inch))
    
    # Procesar imagen si está en el markdown, sino usar la imagen por defecto
    if imagen_encontrada:
        # Obtener la URL de la imagen del markdown
        img_src = imagen_encontrada.get('src', '')
        if img_src:
            # Construir la ruta completa del archivo
            if img_src.startswith('/media/'):
                img_path = img_src.replace('/media/', '')
                img_full_path = os.path.join(settings.MEDIA_ROOT, img_path)
                if os.path.exists(img_full_path):
                    try:
                        img = Image(img_full_path, width=6*inch, height=3.375*inch)
                        story.append(img)
                        story.append(Spacer(1, 0.1*inch))
                        # Usar el caption del markdown si existe, sino usar el por defecto
                        caption_text = f"<i>Figura 1: Mapa satelital del sitio {nombre_sitio}, ubicado en {nombre_zona}, {ciudad}. Coordenadas: {latitud:.6f}°N, {longitud:.6f}°W.</i>"
                        if caption_imagen:
                            caption_text = f"<i>{caption_imagen.get_text()}</i>"
                        story.append(Paragraph(
                            caption_text,
                            ParagraphStyle(
                                'Caption',
                                parent=styles['Normal'],
                                fontSize=8,
                                textColor=colors.HexColor('#666666'),
                                alignment=TA_CENTER,
                                fontName='Helvetica-Oblique'
                            )
                        ))
                    except Exception as e:
                        story.append(Paragraph(f"<i>Error al cargar la imagen del mapa: {str(e)}</i>", body_style))
    
    # Si no hay imagen en el markdown, usar la imagen por defecto
    if not imagen_encontrada:
        try:
            img = Image(mapa_imagen_path, width=6*inch, height=3.375*inch)
            story.append(img)
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(
                f"<i>Figura 1: Mapa satelital del sitio {nombre_sitio}, ubicado en {nombre_zona}, {ciudad}. "
                f"Coordenadas: {latitud:.6f}°N, {longitud:.6f}°W.</i>",
                ParagraphStyle(
                    'Caption',
                    parent=styles['Normal'],
                    fontSize=8,
                    textColor=colors.HexColor('#666666'),
                    alignment=TA_CENTER,
                    fontName='Helvetica-Oblique'
                )
            ))
        except Exception as e:
            story.append(Paragraph(f"<i>Error al cargar la imagen del mapa: {str(e)}</i>", body_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Agregar descripción de acceso al final (sin título)
    if descripcion_acceso_contenido:
        for element in descripcion_acceso_contenido:
            if hasattr(element, 'name') and element.name:
                if element.name == 'p':
                    # Párrafos con formato HTML
                    texto_parrafo = html_to_reportlab(element)
                    if texto_parrafo.strip():
                        story.append(Paragraph(texto_parrafo, body_style))
                elif element.name in ['ul', 'ol']:
                    # Listas
                    for li in element.find_all('li', recursive=False):
                        texto_item = html_to_reportlab(li)
                        # Agregar viñeta o número según el tipo de lista
                        if element.name == 'ul':
                            texto_item = f"• {texto_item}"
                        story.append(Paragraph(texto_item, body_style))
                        story.append(Spacer(1, 0.1*inch))
                elif element.name == 'br':
                    story.append(Spacer(1, 0.1*inch))
                # Ignorar títulos en la sección de acceso
    
    # Construir el PDF
    doc.build(story)
    
    # Guardar archivos en la instancia de ubicación
    with open(output_path, 'rb') as pdf_file:
        ubicacion_instance.documento_pdf.save(
            f'ubicacion_{ubicacion_instance.id}.pdf',
            File(pdf_file),
            save=False
        )
    
    with open(mapa_imagen_path, 'rb') as img_file:
        ubicacion_instance.mapa_imagen.save(
            f'mapa_{ubicacion_instance.id}.png',
            File(img_file),
            save=False
        )
    
    # Actualizar el contenido markdown para incluir la tabla y la imagen
    # Solo si el contenido no fue editado manualmente (contiene las secciones por defecto)
    contenido_actual = ubicacion_instance.contenido or ''
    if '## Descripción de Acceso' in contenido_actual and '## Coordenadas del Sitio' not in contenido_actual:
        # Construir la tabla en markdown
        tabla_markdown = f"""
## Coordenadas del Sitio

| Parámetro | Valor |
|-----------|-------|
| Latitud | {latitud:.6f}° |
| Longitud | {longitud:.6f}° |"""
        
        if distancia_centro:
            tabla_markdown += f"\n| Distancia al centro | {distancia_centro:.2f} km |"
        
        # Construir referencia a la imagen (usando la URL del media)
        imagen_markdown = ""
        if ubicacion_instance.mapa_imagen:
            # Obtener la URL de la imagen (guardar primero para que tenga la URL)
            ubicacion_instance.save(update_fields=['mapa_imagen'])
            imagen_url = ubicacion_instance.mapa_imagen.url
            imagen_markdown = f"""
## Mapa Satelital

![Mapa satelital del sitio {nombre_sitio}]({imagen_url})

*Figura 1: Mapa satelital del sitio {nombre_sitio}, ubicado en {nombre_zona}, {ciudad}. Coordenadas: {latitud:.6f}°N, {longitud:.6f}°W.*
"""
        
        # Insertar tabla e imagen después del contenido principal y antes de la descripción de acceso
        partes_contenido = contenido_actual.split('## Descripción de Acceso')
        if len(partes_contenido) == 2:
            contenido_actualizado = partes_contenido[0].rstrip() + tabla_markdown + imagen_markdown + "\n\n## Descripción de Acceso" + partes_contenido[1]
            ubicacion_instance.contenido = contenido_actualizado
            ubicacion_instance.save(update_fields=['contenido'])
    
    # Limpiar archivos temporales
    try:
        os.remove(output_path)
        os.remove(mapa_imagen_path)
    except:
        pass
    
    return output_path

