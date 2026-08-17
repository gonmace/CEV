from django.db import migrations


def backfill_empresa(apps, schema_editor):
    """Fija Servicio.empresa según la empresa que tenía `creado_por` en este momento —
    best-effort para los datos históricos. De acá en más el campo se fija una sola vez
    al crear el servicio (ver servicios.views.crear_servicio_view) y no se recalcula.

    CatalogoServicios NO necesita backfill: su fila existente queda con empresa=None,
    que es exactamente el catálogo global/base deseado (ver CatalogoServicios.get_activo)."""
    Servicio = apps.get_model('servicios', 'Servicio')
    Profile = apps.get_model('accounts', 'Profile')

    empresa_por_usuario = {
        p.user_id: p.empresa_id
        for p in Profile.objects.filter(empresa__isnull=False)
    }
    for servicio in Servicio.objects.filter(creado_por__isnull=False, empresa__isnull=True):
        empresa_id = empresa_por_usuario.get(servicio.creado_por_id)
        if empresa_id:
            servicio.empresa_id = empresa_id
            servicio.save(update_fields=['empresa'])


class Migration(migrations.Migration):

    dependencies = [
        ('servicios', '0011_catalogoservicios_empresa_servicio_empresa'),
        ('accounts', '0007_marca'),
    ]

    operations = [
        migrations.RunPython(backfill_empresa, migrations.RunPython.noop),
    ]
