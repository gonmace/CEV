from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from proyectos.models import Proyecto, Especificacion
import random
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Genera proyectos de prueba con datos aleatorios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cantidad',
            type=int,
            default=10,
            help='Número de proyectos a generar (default: 10)',
        )
        parser.add_argument(
            '--especificaciones',
            type=int,
            default=5,
            help='Número de especificaciones por proyecto (default: 5)',
        )

    def handle(self, *args, **options):
        cantidad = options['cantidad']
        especificaciones_por_proyecto = options['especificaciones']

        # Obtener usuarios disponibles
        usuarios = list(User.objects.all())
        if not usuarios:
            self.stdout.write(self.style.ERROR('No hay usuarios en la base de datos. Crea al menos un usuario primero.'))
            return

        # Datos de ejemplo
        nombres_proyectos = [
            'Edificio Residencial Las Flores',
            'Centro Comercial Plaza Norte',
            'Hospital Regional Sur',
            'Escuela Primaria San José',
            'Oficinas Corporativas TechHub',
            'Complejo Deportivo Municipal',
            'Torre de Viviendas Vista al Mar',
            'Centro de Investigación Científica',
            'Aeropuerto Internacional Norte',
            'Puente sobre Río Grande',
            'Planta de Tratamiento de Aguas',
            'Parque Tecnológico Industrial',
            'Estación de Metro Central',
            'Biblioteca Pública Municipal',
            'Mercado de Abastos',
            'Hotel Resort Playa Dorada',
            'Estadio Deportivo Nacional',
            'Centro de Convenciones',
            'Terminal de Buses Interurbana',
            'Complejo Turístico Montaña',
        ]

        solicitantes = [
            'Municipalidad de Santiago',
            'Ministerio de Obras Públicas',
            'Empresa Constructora ABC S.A.',
            'Inversiones Inmobiliarias XYZ',
            'Gobierno Regional',
            'Corporación de Desarrollo',
            'Sociedad de Inversiones',
            'Fondo de Infraestructura',
            'Empresa Estatal de Construcción',
            'Consorcio de Empresas',
        ]

        ubicaciones = [
            'Santiago, Región Metropolitana',
            'Valparaíso, Región de Valparaíso',
            'Concepción, Región del Biobío',
            'La Serena, Región de Coquimbo',
            'Antofagasta, Región de Antofagasta',
            'Temuco, Región de La Araucanía',
            'Rancagua, Región de O\'Higgins',
            'Talca, Región del Maule',
            'Arica, Región de Arica y Parinacota',
            'Punta Arenas, Región de Magallanes',
        ]

        descripciones = [
            'Proyecto de infraestructura urbana destinado a mejorar la calidad de vida de los habitantes.',
            'Desarrollo inmobiliario de carácter residencial con áreas verdes y servicios comunitarios.',
            'Inversión en infraestructura pública para el desarrollo económico regional.',
            'Proyecto arquitectónico moderno con enfoque en sostenibilidad y eficiencia energética.',
            'Construcción de instalaciones destinadas a servicios públicos y comunitarios.',
            'Desarrollo de complejo comercial con múltiples tiendas y servicios.',
            'Proyecto de vivienda social para familias de escasos recursos.',
            'Infraestructura educativa con tecnología de punta y espacios modernos.',
            'Centro de salud con equipamiento médico avanzado y múltiples especialidades.',
            'Proyecto turístico destinado a promover el desarrollo económico local.',
        ]

        titulos_especificaciones = [
            'Especificaciones Técnicas Generales',
            'Memoria Descriptiva del Proyecto',
            'Especificaciones de Estructura',
            'Especificaciones de Instalaciones Sanitarias',
            'Especificaciones de Instalaciones Eléctricas',
            'Especificaciones de Instalaciones de Gas',
            'Especificaciones de Terminaciones',
            'Especificaciones de Obras Exteriores',
            'Especificaciones de Seguridad y Protección',
            'Especificaciones de Accesibilidad',
            'Especificaciones de Aislación Térmica',
            'Especificaciones de Aislación Acústica',
            'Especificaciones de Instalaciones Mecánicas',
            'Especificaciones de Señalización',
            'Especificaciones de Paisajismo',
        ]

        contenidos_especificaciones = [
            '''# Especificaciones Técnicas

## 1. Generalidades

El presente proyecto contempla las especificaciones técnicas necesarias para la ejecución de las obras.

### 1.1 Alcance
- Obras de construcción
- Instalaciones especiales
- Obras exteriores

### 1.2 Normativas Aplicables
- Ordenanza General de Urbanismo y Construcciones
- Normas técnicas de construcción
- Reglamentos sectoriales

## 2. Materiales

### 2.1 Hormigón
- Resistencia característica: f'c = 25 MPa
- Agregados según norma NCh 163

### 2.2 Acero
- Barras de refuerzo: A630-420H
- Estructuras metálicas: A36

## 3. Ejecución

Las obras deberán ejecutarse conforme a los planos y especificaciones técnicas aprobadas.
''',
            '''# Memoria Descriptiva

## Descripción del Proyecto

El proyecto consiste en la construcción de [tipo de construcción] ubicado en [ubicación].

## Características Principales

- Superficie construida: [área] m²
- Número de pisos: [pisos]
- Estructura: [tipo de estructura]

## Objetivos

- Mejorar la infraestructura existente
- Proporcionar servicios a la comunidad
- Contribuir al desarrollo urbano

## Consideraciones Especiales

- Cumplimiento de normativas vigentes
- Respeto al medio ambiente
- Eficiencia energética
''',
            '''# Especificaciones de Estructura

## Sistema Estructural

El sistema estructural está compuesto por:

### Elementos Principales
- Fundaciones: Losas de fundación y pilotes
- Estructura: Pórticos de hormigón armado
- Losas: Losas alivianadas

### Materiales Estructurales
- Hormigón: f'c = 25 MPa
- Acero: A630-420H
- Mampostería: Bloques de hormigón

## Diseño Estructural

El diseño estructural cumple con las normativas vigentes y considera:
- Cargas permanentes
- Sobrecargas de uso
- Cargas de viento y sismo
''',
        ]

        proyectos_creados = 0
        especificaciones_creadas = 0

        self.stdout.write(self.style.SUCCESS(f'Generando {cantidad} proyectos de prueba...'))

        for i in range(cantidad):
            # Seleccionar datos aleatorios
            nombre = random.choice(nombres_proyectos)
            solicitante = random.choice(solicitantes)
            ubicacion = random.choice(ubicaciones)
            descripcion = random.choice(descripciones)
            usuario = random.choice(usuarios)
            
            # Fecha aleatoria en los últimos 6 meses
            fecha_base = datetime.now() - timedelta(days=random.randint(0, 180))
            
            # Crear proyecto
            proyecto = Proyecto.objects.create(
                nombre=nombre,
                solicitante=solicitante,
                ubicacion=ubicacion,
                descripcion=descripcion,
                creado_por=usuario,
                activo=True,
                publico=random.choice([True, False]),
                fecha_creacion=fecha_base,
                fecha_actualizacion=fecha_base + timedelta(days=random.randint(0, 30))
            )
            proyectos_creados += 1

            # Crear especificaciones para el proyecto
            titulos_disponibles = titulos_especificaciones.copy()
            for j in range(especificaciones_por_proyecto):
                if not titulos_disponibles:
                    titulos_disponibles = titulos_especificaciones.copy()
                
                titulo = random.choice(titulos_disponibles)
                titulos_disponibles.remove(titulo)
                
                contenido = random.choice(contenidos_especificaciones)
                
                fecha_esp = fecha_base + timedelta(days=random.randint(1, 60))
                
                especificacion = Especificacion.objects.create(
                    proyecto=proyecto,
                    titulo=titulo,
                    contenido=contenido,
                    orden=j + 1,
                    fecha_creacion=fecha_esp,
                    fecha_actualizacion=fecha_esp + timedelta(days=random.randint(0, 20))
                )
                especificaciones_creadas += 1

            if (i + 1) % 5 == 0:
                self.stdout.write(f'  Progreso: {i + 1}/{cantidad} proyectos creados...')

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Proceso completado:\n'
            f'  - Proyectos creados: {proyectos_creados}\n'
            f'  - Especificaciones creadas: {especificaciones_creadas}'
        ))

