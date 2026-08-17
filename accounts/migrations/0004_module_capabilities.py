"""Reemplaza el catálogo de capacidades por el de acceso a módulos.

Las 7 capacidades anteriores (proyectos.create, pliegos.generate, accounts.manage, …)
nunca llegaron a comprobarse en ninguna vista: eran configurables pero no gobernaban
nada. Se borran sus filas y se siembran las 3 nuevas, que sí se aplican
(ModuleAccessMiddleware y los filtros de visibilidad).

Los valores van inline y NO se importan de accounts.permissions: una migración debe
significar siempre lo mismo, aunque el catálogo del código cambie más adelante.
"""
from django.db import migrations

CAPABILITIES = ['pliegos.access', 'servicios.access', 'data.view_all']

DEFAULTS = {
    # El Usuario entra a ambos módulos: es lo que podía hacer antes de que existieran
    # los permisos de módulo, así que nadie pierde acceso al aplicar esta migración.
    'USUARIO': {'pliegos.access', 'servicios.access'},
    'ADMINISTRADOR': {'pliegos.access', 'servicios.access', 'data.view_all'},
}


def migrar_capacidades(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    UserPermission = apps.get_model('accounts', 'UserPermission')

    # Fuera las capacidades del catálogo viejo (y cualquier override individual sobre ellas).
    RolePermission.objects.exclude(capability__in=CAPABILITIES).delete()
    UserPermission.objects.exclude(capability__in=CAPABILITIES).delete()

    for role, enabled_caps in DEFAULTS.items():
        for capability in CAPABILITIES:
            RolePermission.objects.update_or_create(
                role=role, capability=capability,
                defaults={'enabled': capability in enabled_caps},
            )


def revertir(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    UserPermission = apps.get_model('accounts', 'UserPermission')
    RolePermission.objects.filter(capability__in=CAPABILITIES).delete()
    UserPermission.objects.filter(capability__in=CAPABILITIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_backfill_profiles'),
    ]

    operations = [
        migrations.RunPython(migrar_capacidades, revertir),
    ]
