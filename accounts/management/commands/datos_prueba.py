"""Datos de prueba: empresas y cuentas que cubren los casos límite del sistema.

    python manage.py datos_prueba            # crea (o actualiza) los datos
    python manage.py datos_prueba --limpiar  # los borra y sale

No es una fixture cualquiera: cada empresa y cada cuenta existe para poder ver un caso
concreto en pantalla sin tener que prepararlo a mano (empresa llena, empresa sin saldo,
empresa inactiva, usuario con tope alcanzado, cuenta sin activar…).

Todo lo que crea usa dominios `.test` (reservado por la RFC 2606: nunca va a existir de
verdad) y el prefijo `pruebaN` en los usernames, así que `--limpiar` no puede llevarse por
delante datos reales.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.creditos import fijar
from accounts.models import (
    AllowedEmail, BolsaCreditos, ConsumoCredito, Empresa, Profile, Role, TopeUsuario,
)

User = get_user_model()

PASSWORD = 'prueba1234'
PREFIJO = 'prueba_'          # marca los usuarios creados por este comando
DOMINIOS = ['andes.test', 'sur.test', 'norte.test']

PLIEGOS = 'pliegos.access'
SERVICIOS = 'servicios.access'


class Command(BaseCommand):
    help = 'Crea empresas y cuentas de prueba (o las borra con --limpiar).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar', action='store_true',
            help='Borra los datos de prueba en vez de crearlos.',
        )

    def handle(self, *args, **opciones):
        if opciones['limpiar']:
            self._limpiar()
            return
        with transaction.atomic():
            self._crear()

    # ── Limpieza ────────────────────────────────────────────────────────────

    def _limpiar(self):
        usuarios = User.objects.filter(username__startswith=PREFIJO)
        n_users = usuarios.count()
        usuarios.delete()  # arrastra Profile, bolsas, topes (CASCADE)
        n_emp, _ = Empresa.objects.filter(dominio__in=DOMINIOS).delete()
        n_mail, _ = AllowedEmail.objects.filter(email__endswith='.test').delete()
        self.stdout.write(self.style.SUCCESS(
            f'Borrados: {n_users} usuarios, {n_emp} objetos de empresas, {n_mail} correos permitidos.'
        ))

    # ── Creación ────────────────────────────────────────────────────────────

    def _usuario(self, nombre, apellido, email, empresa=None, rol=Role.USUARIO,
                 activo=True, sin_activar=False):
        """Crea (o actualiza) una cuenta. `sin_activar` = invitada que nunca entró:
        inactiva y sin contraseña usable, que es como las cuenta el panel de Cuentas."""
        user, _ = User.objects.get_or_create(
            username=f'{PREFIJO}{email.split("@")[0]}_{email.split("@")[1].split(".")[0]}',
            defaults={'email': email},
        )
        user.email = email
        user.first_name = nombre
        user.last_name = apellido
        user.is_active = activo and not sin_activar
        if sin_activar:
            user.set_unusable_password()
        else:
            user.set_password(PASSWORD)
        user.save()
        Profile.objects.update_or_create(
            user=user, defaults={'role': rol, 'empresa': empresa},
        )
        return user

    def _crear(self):
        # ── Empresas: cada una monta un escenario distinto ───────────────────
        andes, _ = Empresa.objects.update_or_create(
            dominio='andes.test',
            defaults={
                'nombre': 'Constructora Andes', 'max_usuarios': 8, 'is_active': True,
                'note': 'Caso normal: con plazas libres y saldo en los dos módulos.',
            },
        )
        sur, _ = Empresa.objects.update_or_create(
            dominio='sur.test',
            defaults={
                'nombre': 'Ingeniería Sur', 'max_usuarios': 2, 'is_active': True,
                'note': 'Caso CUPO LLENO: 2 contratados y 2 activos, no admite más altas.',
            },
        )
        norte, _ = Empresa.objects.update_or_create(
            dominio='norte.test',
            defaults={
                'nombre': 'Obras del Norte', 'max_usuarios': 5, 'is_active': False,
                'note': 'Caso INACTIVA y SIN CRÉDITOS: su gente no puede entrar ni generar.',
            },
        )

        fijar(andes, PLIEGOS, 50)
        fijar(andes, SERVICIOS, 25)
        fijar(sur, PLIEGOS, 3)       # poco saldo: se agota rápido probando
        fijar(sur, SERVICIOS, 0)     # sin saldo en Servicios
        fijar(norte, PLIEGOS, 0)
        fijar(norte, SERVICIOS, 0)

        # ── Cuentas de empresa ──────────────────────────────────────────────
        # Andes (4 de 8 plazas): un administrador, dos usuarios y uno con tope.
        self._usuario('Laura', 'Vidal', 'laura@andes.test', andes, Role.ADMINISTRADOR)
        self._usuario('Pedro', 'Rojas', 'pedro@andes.test', andes)
        topeado = self._usuario('Sofía', 'Núñez', 'sofia@andes.test', andes)
        self._usuario('Iván', 'Bravo', 'ivan@andes.test', andes, sin_activar=True)

        # Sofía tiene un tope de 2 y ya los gastó: sirve para ver el "2/2" en rojo y que el
        # bloqueo por tope funciona aunque la empresa tenga saldo de sobra.
        TopeUsuario.objects.update_or_create(
            usuario=topeado, modulo=PLIEGOS, defaults={'tope': 2},
        )
        ConsumoCredito.objects.filter(usuario=topeado).delete()
        for i in range(2):
            ConsumoCredito.objects.create(
                usuario=topeado, empresa=andes, modulo=PLIEGOS,
                referencia=f'EspecificacionTecnica#{900 + i}',
            )

        # Sur: llena (2 de 2). Invitar a alguien más de este dominio debe rebotar.
        self._usuario('Marta', 'Silva', 'marta@sur.test', sur, Role.ADMINISTRADOR)
        self._usuario('Diego', 'Paz', 'diego@sur.test', sur)

        # Norte: empresa inactiva, con gente dentro.
        self._usuario('Elena', 'Ortiz', 'elena@norte.test', norte)
        self._usuario('Hugo', 'Mena', 'hugo@norte.test', norte)

        # ── Cuentas personales (sin empresa) ────────────────────────────────
        ana = self._usuario('Ana', 'Torres', 'ana@personal.test')
        fijar(ana, PLIEGOS, 10)
        fijar(ana, SERVICIOS, 4)

        seco = self._usuario('Bruno', 'Lagos', 'bruno@personal.test')
        fijar(seco, PLIEGOS, 0)      # sin saldo: al generar debe salir el bloqueo
        fijar(seco, SERVICIOS, 0)

        self._usuario('Carla', 'Díaz', 'carla@personal.test', sin_activar=True)

        # Las cuentas personales entran por invitación individual, no por dominio.
        for correo in ('ana@personal.test', 'bruno@personal.test', 'carla@personal.test'):
            AllowedEmail.objects.update_or_create(
                email=correo, defaults={'is_active': True},
            )

        self._poblar_magoreal()
        self._resumen(andes, sur, norte)

    def _poblar_magoreal(self):
        """Compañeros de equipo para Magoreal, que es una empresa REAL del sistema.

        No se crea ni se modifica la empresa (ni su cupo ni sus créditos): solo se le cuelgan
        cuentas, y únicamente si ya existe. Si no está, no se hace nada — este comando no
        debe inventar empresas reales.

        Los usuarios llevan igual el prefijo `prueba_`, así que `--limpiar` se los lleva y
        deja la empresa como estaba.
        """
        magoreal = Empresa.objects.filter(dominio='magoreal.com').first()
        if not magoreal:
            self.stdout.write(self.style.WARNING(
                'No existe la empresa magoreal.com: no se agregaron cuentas para ella.'
            ))
            return

        equipo = [
            ('Valentina', 'Rivas', 'valentina@magoreal.com', Role.ADMINISTRADOR),
            ('Matías', 'Fuentes', 'matias@magoreal.com', Role.USUARIO),
            ('Camila', 'Herrera', 'camila@magoreal.com', Role.USUARIO),
        ]
        for nombre, apellido, email, rol in equipo:
            self._usuario(nombre, apellido, email, magoreal, rol)

        # Un consumo suelto para que la columna de gasto no salga toda en cero.
        matias = User.objects.get(email='matias@magoreal.com')
        ConsumoCredito.objects.filter(usuario=matias).delete()
        ConsumoCredito.objects.create(
            usuario=matias, empresa=magoreal, modulo=PLIEGOS,
            referencia='EspecificacionTecnica#910',
        )

        self.magoreal = magoreal

    def _resumen(self, andes, sur, norte):
        self.stdout.write(self.style.SUCCESS('\nDatos de prueba creados.\n'))
        self.stdout.write(f'  Contraseña de todas las cuentas activas: {PASSWORD}\n')

        self.stdout.write(self.style.MIGRATE_HEADING('\nEmpresas'))
        magoreal = getattr(self, 'magoreal', None)
        for e in [x for x in (andes, sur, norte, magoreal) if x]:
            saldos = {b.modulo: b.creditos for b in BolsaCreditos.objects.filter(empresa=e)}
            estado = 'activa' if e.is_active else 'INACTIVA'
            self.stdout.write(
                f'  {e.nombre:22} {e.dominio:14} {estado:8} '
                f'{e.usuarios_activos}/{e.max_usuarios} usuarios · '
                f'Proyectos: {saldos.get(PLIEGOS, 0)} · Servicios: {saldos.get(SERVICIOS, 0)}'
            )
            self.stdout.write(f'    └─ {e.note}')

        self.stdout.write(self.style.MIGRATE_HEADING('\nQué se puede probar'))
        for linea in (
            'laura@andes.test    Administrador: ve los datos de TODAS las cuentas',
            'sofia@andes.test    tope de 2 créditos ya gastado: no puede generar aunque Andes tenga 50',
            'pedro@andes.test    usuario normal de empresa: consume de la bolsa común',
            'marta@sur.test      su empresa está LLENA: invitar a otro de @sur.test debe rebotar',
            'elena@norte.test    su empresa está INACTIVA y sin créditos',
            'ana@personal.test   cuenta personal CON créditos (sin tarjeta de Usuarios en el panel)',
            'bruno@personal.test cuenta personal SIN créditos: al generar debe bloquearse',
            'carla@personal.test invitada que nunca activó (sale en "Sin activar")',
            'ivan@andes.test     invitado de empresa que nunca activó',
            'valentina@magoreal.com  Administradora de Magoreal',
            'matias@magoreal.com     usuario de Magoreal (ya gastó 1 crédito)',
            'camila@magoreal.com     usuaria de Magoreal',
        ):
            self.stdout.write(f'  {linea}')
        self.stdout.write(
            self.style.WARNING('\n  Para borrarlo todo: python manage.py datos_prueba --limpiar\n')
        )
