"""Tests de aislamiento entre empresas y permisos del flujo de pliegos.

Cubren los IDOR/fugas cross-tenant encontrados en la auditoría previa al lanzamiento
(ver AUDITORIA.md, sección "multi-tenancy, créditos y cuentas"): un test de pocas
líneas por caso habría cazado cada uno de estos bugs antes de que llegaran a producción.
"""
import json

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from accounts.models import Empresa, Profile
from proyectos.models import Proyecto
from . import views
from .models import EspecificacionTecnica

User = get_user_model()


class AislamientoEntreEmpresasTests(TestCase):
    """`pasos_view` es la única vista del módulo con lógica de permisos "a mano" en
    vez de `accounts.permissions.puede_ver/puede_editar` directo — por eso fue donde
    aparecieron las fugas."""

    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='A', dominio='a.test', max_usuarios=5)
        self.empresa_b = Empresa.objects.create(nombre='B', dominio='b.test', max_usuarios=5)

        self.user_a = User.objects.create_user(username='ua', email='u@a.test', password='x')
        Profile.objects.create(user=self.user_a, empresa=self.empresa_a)
        self.user_b = User.objects.create_user(username='ub', email='u@b.test', password='x')
        Profile.objects.create(user=self.user_b, empresa=self.empresa_b)

        self.proyecto_b = Proyecto.objects.create(
            nombre='Proyecto de B', creado_por=self.user_b, empresa=self.empresa_b,
        )

        self.client = Client()
        self.client.force_login(self.user_a)

    def test_proyecto_id_ajeno_no_se_fija_en_sesion(self):
        # Antes: `puede_ver` fallaba pero `proyecto_id` seguía apuntando al proyecto
        # de B, y `pasos_view` lo usaba igual más abajo (pasaba por alto el chequeo).
        self.client.get(reverse('pliego_licitacion:pasos'), {
            'paso': 1, 'proyecto_id': self.proyecto_b.id,
        })
        session = self.client.session
        self.assertNotIn('pliego_proyecto_id', session)

    def test_no_se_listan_ni_re_vinculan_borradores_de_proyecto_ajeno(self):
        """Antes: un borrador huérfano propio se re-vinculaba (UPDATE) al proyecto
        ajeno con solo pasar `?proyecto_id=<el de otra empresa>` — sin pasar por
        `puede_editar`."""
        huerfano = EspecificacionTecnica.objects.create(
            titulo='Borrador de A', descripcion='...', tipo_servicio='Mecánico',
            creado_por=self.user_a, empresa=self.empresa_a, paso=2,
        )
        resp = self.client.get(reverse('pliego_licitacion:pasos'), {
            'paso': 1, 'proyecto_id': self.proyecto_b.id,
        })
        self.assertEqual(resp.status_code, 200)
        huerfano.refresh_from_db()
        self.assertIsNone(huerfano.proyecto_id, 'no debe quedar vinculado al proyecto de otra empresa')
        # Tampoco debe aparecer listado en el contexto (nunca se vio el proyecto de B).
        self.assertNotEqual(resp.context.get('proyecto_id'), self.proyecto_b.id)

    def test_no_se_puede_crear_borrador_en_proyecto_ajeno(self):
        """`coherencia_view` valida `puede_ver` sobre el `proyecto_id` del payload
        antes de colgar la EspecificacionTecnica de ese proyecto."""
        resp = self.client.post(
            reverse('pliego_licitacion:coherencia'),
            data=json.dumps({
                'titulo': 'x', 'descripcion': 'x', 'tipo_servicio': 'Mecánico',
                'unidad_medida': 'glb', 'proyecto_id': self.proyecto_b.id,
            }),
            content_type='application/json',
        )
        # El webhook de coherencia no existe en el entorno de test: falla más abajo,
        # pero lo que importa es que la especificación, si se llegó a crear, no quedó
        # colgada del proyecto ajeno.
        creada = EspecificacionTecnica.objects.filter(creado_por=self.user_a).first()
        if creada is not None:
            self.assertIsNone(creada.proyecto_id)


class BypassPorCreadoPorNuloTests(TestCase):
    """`creado_por` es SET_NULL: un borrador huérfano no debe volverse editable por
    cualquiera solo por perder a su creador."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='A', dominio='a.test', max_usuarios=5)
        self.dueno = User.objects.create_user(username='d', email='d@a.test', password='x')
        Profile.objects.create(user=self.dueno, empresa=self.empresa)

        self.intruso = User.objects.create_user(username='i', email='i@otra.test', password='x')
        Profile.objects.create(user=self.intruso)

        self.huerfano = EspecificacionTecnica.objects.create(
            titulo='Huérfano', descripcion='...', tipo_servicio='Mecánico',
            creado_por=None, empresa=self.empresa,
        )

    def test_usuario_sin_relacion_no_puede_editar_borrador_huerfano(self):
        # Nota: `actualizar_cantidad_especificacion_tecnica_view` no está enrutada en
        # `urls.py` (código muerto, ver AUDITORIA.md) — se invoca directo con
        # RequestFactory para probar la lógica de permisos igual. El chequeo de
        # `puede_editar` corta ANTES de tocar `cantidad`, así que el bug de esta vista
        # (referencia un campo `cantidad` que ya no existe en el modelo) no interfiere.
        factory = RequestFactory()
        request = factory.post(
            f'/pliego/especificacion/{self.huerfano.id}/cantidad/',
            data=json.dumps({'cantidad': '999'}),
            content_type='application/json',
        )
        request.user = self.intruso
        resp = views.actualizar_cantidad_especificacion_tecnica_view(request, self.huerfano.id)

        self.assertEqual(resp.status_code, 403)
