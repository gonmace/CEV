#!/usr/bin/env python
"""
Script para crear usuarios ficticios de prueba.
Ejecutar desde la raíz del proyecto: python junk/crear_usuarios_prueba.py
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

USUARIOS_PRUEBA = [
    {
        'username': 'maria.garcia',
        'email': 'maria.garcia@ejemplo.cl',
        'first_name': 'María',
        'last_name': 'García López',
        'password': 'test1234',
    },
    {
        'username': 'carlos.munoz',
        'email': 'carlos.munoz@ejemplo.cl',
        'first_name': 'Carlos',
        'last_name': 'Muñoz Silva',
        'password': 'test1234',
    },
    {
        'username': 'ana.rodriguez',
        'email': 'ana.rodriguez@ejemplo.cl',
        'first_name': 'Ana',
        'last_name': 'Rodríguez Pérez',
        'password': 'test1234',
    },
    {
        'username': 'pedro.sanchez',
        'email': 'pedro.sanchez@ejemplo.cl',
        'first_name': 'Pedro',
        'last_name': 'Sánchez Torres',
        'password': 'test1234',
    },
    {
        'username': 'lucia.fernandez',
        'email': 'lucia.fernandez@ejemplo.cl',
        'first_name': 'Lucía',
        'last_name': 'Fernández Rojas',
        'password': 'test1234',
    },
]


def main():
    creados = 0
    existentes = 0

    print('Creando usuarios de prueba...\n')

    for datos in USUARIOS_PRUEBA:
        if User.objects.filter(username=datos['username']).exists():
            print(f"  [skip] {datos['username']} ya existe")
            existentes += 1
            continue

        User.objects.create_user(
            username=datos['username'],
            email=datos['email'],
            password=datos['password'],
            first_name=datos['first_name'],
            last_name=datos['last_name'],
        )
        print(f"  [ok] {datos['username']} ({datos['first_name']} {datos['last_name']})")
        creados += 1

    print(f'\nListo: {creados} creados, {existentes} ya existían.')
    print('\nCredenciales de prueba (todos usan password: test1234):')
    for u in USUARIOS_PRUEBA:
        print(f"  - {u['username']}")


if __name__ == '__main__':
    main()
