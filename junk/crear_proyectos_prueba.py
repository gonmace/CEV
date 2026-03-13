#!/usr/bin/env python
"""
Script para crear proyectos de prueba usando los usuarios existentes.
Ejecutar desde la raíz del proyecto: python junk/crear_proyectos_prueba.py
Opciones: --cantidad 10 --especificaciones 5
"""
import argparse
import os
import random
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from proyectos.models import Proyecto, Especificacion

NOMBRES_PROYECTOS = [
    'Edificio Residencial Las Flores',
    'Centro Comercial Plaza Norte',
    'Hospital Regional Sur',
    'Escuela Primaria San Jose',
    'Oficinas Corporativas TechHub',
    'Complejo Deportivo Municipal',
    'Torre de Viviendas Vista al Mar',
    'Centro de Investigacion Cientifica',
    'Aeropuerto Internacional Norte',
    'Puente sobre Rio Grande',
    'Planta de Tratamiento de Aguas',
    'Parque Tecnologico Industrial',
    'Estacion de Metro Central',
    'Biblioteca Publica Municipal',
    'Mercado de Abastos',
]

SOLICITANTES = [
    'Municipalidad de Santiago',
    'Ministerio de Obras Publicas',
    'Empresa Constructora ABC S.A.',
    'Inversiones Inmobiliarias XYZ',
    'Gobierno Regional',
    'Corporacion de Desarrollo',
    'Sociedad de Inversiones',
    'Fondo de Infraestructura',
]

UBICACIONES = [
    'Santiago, Region Metropolitana',
    'Valparaiso, Region de Valparaiso',
    'Concepcion, Region del Biobio',
    'La Serena, Region de Coquimbo',
    'Antofagasta, Region de Antofagasta',
    'Temuco, Region de La Araucania',
    'Rancagua, Region de O\'Higgins',
    'Talca, Region del Maule',
]

DESCRIPCIONES = [
    'Proyecto de infraestructura urbana destinado a mejorar la calidad de vida.',
    'Desarrollo inmobiliario residencial con areas verdes y servicios comunitarios.',
    'Inversion en infraestructura publica para el desarrollo economico regional.',
    'Proyecto arquitectonico moderno con enfoque en sostenibilidad.',
    'Construccion de instalaciones para servicios publicos y comunitarios.',
]

TITULOS_ESPECIFICACIONES = [
    'Especificaciones Tecnicas Generales',
    'Memoria Descriptiva del Proyecto',
    'Especificaciones de Estructura',
    'Especificaciones de Instalaciones Sanitarias',
    'Especificaciones de Instalaciones Electricas',
    'Especificaciones de Terminaciones',
    'Especificaciones de Obras Exteriores',
    'Especificaciones de Seguridad y Proteccion',
    'Especificaciones de Accesibilidad',
    'Especificaciones de Paisajismo',
]

CONTENIDO_ESPECIFICACION = '''# Especificaciones Tecnicas

## 1. Generalidades

El presente proyecto contempla las especificaciones tecnicas necesarias para la ejecucion de las obras.

### 1.1 Alcance
- Obras de construccion
- Instalaciones especiales
- Obras exteriores

### 1.2 Normativas Aplicables
- Ordenanza General de Urbanismo y Construcciones
- Normas tecnicas de construccion

## 2. Materiales

### 2.1 Hormigon
- Resistencia caracteristica: f'c = 25 MPa

### 2.2 Acero
- Barras de refuerzo: A630-420H
'''


def main():
    parser = argparse.ArgumentParser(description='Crear proyectos de prueba')
    parser.add_argument('--cantidad', type=int, default=10, help='Numero de proyectos (default: 10)')
    parser.add_argument('--especificaciones', type=int, default=5, help='Especificaciones por proyecto (default: 5)')
    args = parser.parse_args()

    usuarios = list(User.objects.all())
    if not usuarios:
        print('ERROR: No hay usuarios. Ejecuta primero: python junk/crear_usuarios_prueba.py')
        sys.exit(1)

    cantidad = args.cantidad
    espec_por_proyecto = args.especificaciones

    print(f'Creando {cantidad} proyectos con {espec_por_proyecto} especificaciones cada uno...\n')

    proyectos_creados = 0
    especificaciones_creadas = 0

    for i in range(cantidad):
        usuario = random.choice(usuarios)
        proyecto = Proyecto.objects.create(
            nombre=random.choice(NOMBRES_PROYECTOS),
            solicitante=random.choice(SOLICITANTES),
            ubicacion=random.choice(UBICACIONES),
            descripcion=random.choice(DESCRIPCIONES),
            creado_por=usuario,
            activo=True,
            publico=random.choice([True, False]),
        )
        proyectos_creados += 1
        print(f"  [ok] {proyecto.nombre} (por {usuario.username})")

        titulos_disp = TITULOS_ESPECIFICACIONES.copy()
        for j in range(espec_por_proyecto):
            if not titulos_disp:
                titulos_disp = TITULOS_ESPECIFICACIONES.copy()
            titulo = random.choice(titulos_disp)
            titulos_disp.remove(titulo)

            Especificacion.objects.create(
                proyecto=proyecto,
                titulo=titulo,
                contenido=CONTENIDO_ESPECIFICACION,
                orden=j + 1,
                token_cost=round(random.uniform(0.5, 5.0), 2),
            )
            especificaciones_creadas += 1

    print(f'\nListo: {proyectos_creados} proyectos, {especificaciones_creadas} especificaciones.')


if __name__ == '__main__':
    main()
