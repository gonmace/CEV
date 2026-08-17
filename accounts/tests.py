"""Tests del sistema de créditos y de los dos tipos de cuenta (empresa / personal)."""
from allauth.account.adapter import get_adapter
from allauth.socialaccount.adapter import get_adapter as get_social_adapter
from django.contrib.auth import get_user_model
from django.test import TestCase

from .access import is_email_allowed, resolve_empresa
from .creditos import (
    SinCreditos, consumir, consumido_por, equipo_de, puede_consumir, recargar, revertir, saldo,
)
from .models import BolsaCreditos, ConsumoCredito, Empresa, Profile, TopeUsuario

User = get_user_model()

PLIEGOS = 'pliegos.access'
SERVICIOS = 'servicios.access'


class CreditosTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre='Acme', dominio='acme.com', max_usuarios=2,
        )
        self.empleado = User.objects.create_user(
            username='emp', email='ana@acme.com', password='x', is_active=True)
        Profile.objects.create(user=self.empleado, empresa=self.empresa)

        self.personal = User.objects.create_user(
            username='per', email='juan@gmail.com', password='x', is_active=True)
        Profile.objects.create(user=self.personal)

    def test_empleado_consume_de_la_bolsa_de_su_empresa(self):
        recargar(self.empresa, PLIEGOS, 3)
        self.assertEqual(saldo(self.empleado, PLIEGOS), 3)

        consumir(self.empleado, PLIEGOS, referencia='EspecificacionTecnica#1')

        self.assertEqual(saldo(self.empleado, PLIEGOS), 2)
        # El descuento salió de la empresa, no de una bolsa personal del empleado.
        self.assertFalse(BolsaCreditos.objects.filter(usuario=self.empleado).exists())
        consumo = ConsumoCredito.objects.get()
        self.assertEqual(consumo.empresa, self.empresa)
        self.assertEqual(consumo.usuario, self.empleado)

    def test_cuenta_personal_consume_de_su_propia_bolsa(self):
        recargar(self.personal, SERVICIOS, 1)
        consumir(self.personal, SERVICIOS, referencia='Servicio#1')

        self.assertEqual(saldo(self.personal, SERVICIOS), 0)
        self.assertIsNone(ConsumoCredito.objects.get().empresa)

    def test_los_creditos_son_por_modulo(self):
        recargar(self.empresa, PLIEGOS, 5)
        # Tener saldo en Licitación no da derecho a generar en Servicios.
        self.assertEqual(saldo(self.empleado, SERVICIOS), 0)
        ok, motivo = puede_consumir(self.empleado, SERVICIOS)
        self.assertFalse(ok)
        self.assertIn('créditos', motivo)

    def test_sin_saldo_no_se_puede_consumir(self):
        ok, motivo = puede_consumir(self.empleado, PLIEGOS)
        self.assertFalse(ok)
        self.assertIn('Acme', motivo)  # el mensaje nombra a la empresa
        with self.assertRaises(SinCreditos):
            consumir(self.empleado, PLIEGOS)
        self.assertEqual(ConsumoCredito.objects.count(), 0)

    def test_tope_individual_limita_aunque_la_empresa_tenga_saldo(self):
        recargar(self.empresa, PLIEGOS, 100)
        TopeUsuario.objects.create(usuario=self.empleado, modulo=PLIEGOS, tope=2)

        consumir(self.empleado, PLIEGOS)
        consumir(self.empleado, PLIEGOS)

        ok, motivo = puede_consumir(self.empleado, PLIEGOS)
        self.assertFalse(ok, 'el tope individual debe cortar aunque quede saldo en la bolsa')
        self.assertIn('límite personal', motivo)
        with self.assertRaises(SinCreditos):
            consumir(self.empleado, PLIEGOS)

        self.assertEqual(consumido_por(self.empleado, PLIEGOS), 2)
        self.assertEqual(saldo(self.empleado, PLIEGOS), 98)  # la bolsa sigue con saldo

    def test_el_tope_de_uno_no_afecta_a_otro_miembro(self):
        otro = User.objects.create_user(
            username='otro', email='beto@acme.com', password='x', is_active=True)
        Profile.objects.create(user=otro, empresa=self.empresa)
        recargar(self.empresa, PLIEGOS, 10)
        TopeUsuario.objects.create(usuario=self.empleado, modulo=PLIEGOS, tope=1)

        consumir(self.empleado, PLIEGOS)
        self.assertFalse(puede_consumir(self.empleado, PLIEGOS)[0])
        # El compañero, sin tope, sigue pudiendo gastar de la bolsa común.
        self.assertTrue(puede_consumir(otro, PLIEGOS)[0])

    def test_superuser_no_consume(self):
        su = User.objects.create_superuser(username='su', email='su@x.io', password='x')
        self.assertIsNone(saldo(su, PLIEGOS))          # ilimitado
        self.assertTrue(puede_consumir(su, PLIEGOS)[0])
        consumir(su, PLIEGOS)
        self.assertEqual(ConsumoCredito.objects.count(), 0)

    def test_revertir_devuelve_el_credito_y_borra_el_consumo(self):
        # Caso real: `generar_resultado_view` cobra ANTES de saber si n8n va a responder
        # bien (para reservar el crédito y cerrar la carrera de dos generaciones a la
        # vez); si el webhook falla después, hay que deshacer ese cobro.
        recargar(self.empresa, PLIEGOS, 3)
        consumir(self.empleado, PLIEGOS, referencia='EspecificacionTecnica#9')
        self.assertEqual(saldo(self.empleado, PLIEGOS), 2)

        revertir(self.empleado, PLIEGOS, referencia='EspecificacionTecnica#9')

        self.assertEqual(saldo(self.empleado, PLIEGOS), 3, 'el crédito debe volver a la bolsa')
        self.assertEqual(ConsumoCredito.objects.count(), 0, 'no debe quedar rastro del cobro deshecho')

    def test_revertir_sin_nada_que_revertir_no_hace_nada(self):
        revertir(self.empleado, PLIEGOS, referencia='EspecificacionTecnica#inexistente')
        self.assertEqual(saldo(self.empleado, PLIEGOS), 0)


class CupoEmpresaTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre='Acme', dominio='acme.com', max_usuarios=1,
        )

    def test_el_dominio_resuelve_la_empresa(self):
        self.assertEqual(resolve_empresa('ana@acme.com'), self.empresa)
        self.assertIsNone(resolve_empresa('juan@gmail.com'))

    def test_no_se_admiten_altas_por_encima_del_cupo(self):
        self.assertTrue(is_email_allowed('ana@acme.com'))

        u = User.objects.create_user(
            username='u', email='ana@acme.com', password='x', is_active=True)
        Profile.objects.create(user=u, empresa=self.empresa)

        # La empresa contrató 1 usuario y ya lo tiene: el siguiente correo del dominio
        # deja de estar permitido hasta que amplíen el cupo.
        self.assertFalse(self.empresa.hay_cupo)
        self.assertFalse(is_email_allowed('beto@acme.com'))

    def test_una_cuenta_inactiva_libera_plaza(self):
        u = User.objects.create_user(
            username='u', email='ana@acme.com', password='x', is_active=False)
        Profile.objects.create(user=u, empresa=self.empresa)
        self.assertTrue(self.empresa.hay_cupo, 'las bajas no deben ocupar plaza')


class RegistroCerradoTests(TestCase):
    """El registro (email+contraseña y Google) solo debe ser posible por el flujo
    propio (`request_access` + link de activación) o para correos en la allow-list.

    Antes de `accounts/adapters.py`, faltaban ACCOUNT_ADAPTER/SOCIALACCOUNT_ADAPTER y
    allauth caía en su default (`is_open_for_signup` -> True): cualquiera podía crear
    una cuenta activa en `/accounts/signup/` o con cualquier cuenta de Google, sin
    Profile, sin empresa y sin pasar por `accounts.access.is_email_allowed`.
    """

    def test_signup_por_email_esta_cerrado(self):
        self.assertFalse(get_adapter().is_open_for_signup(None))

    def test_social_login_exige_correo_habilitado(self):
        empresa = Empresa.objects.create(nombre='Acme', dominio='acme.com', max_usuarios=5)

        class _SocialLoginFalso:
            def __init__(self, email):
                self.user = User(email=email)

        adapter = get_social_adapter()
        self.assertTrue(adapter.is_open_for_signup(None, _SocialLoginFalso('nueva@acme.com')))
        self.assertFalse(adapter.is_open_for_signup(None, _SocialLoginFalso('nadie@evil.com')))


class EquipoDashboardTests(TestCase):
    def test_cuenta_personal_no_tiene_equipo(self):
        u = User.objects.create_user(username='p', email='p@gmail.com', password='x')
        Profile.objects.create(user=u)
        self.assertIsNone(equipo_de(u), 'una cuenta personal no debe ver el contador de usuarios')

    def test_cuenta_de_empresa_ve_solo_los_suyos(self):
        empresa = Empresa.objects.create(nombre='Acme', dominio='acme.com', max_usuarios=20)
        u = User.objects.create_user(
            username='a', email='a@acme.com', password='x', is_active=True)
        Profile.objects.create(user=u, empresa=empresa)
        # Un usuario de OTRA empresa no debe contar en el equipo de Acme.
        otra = Empresa.objects.create(nombre='Otra', dominio='otra.com')
        ajeno = User.objects.create_user(
            username='z', email='z@otra.com', password='x', is_active=True)
        Profile.objects.create(user=ajeno, empresa=otra)

        self.assertEqual(equipo_de(u), {'usados': 1, 'contratados': 20, 'nombre': 'Acme'})
