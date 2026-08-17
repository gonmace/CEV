from django.db import migrations


def backfill_empresa(apps, schema_editor):
    """Fija Proyecto.empresa según la empresa que tenía `creado_por` en este momento —
    best-effort para los datos históricos. De acá en más el campo se fija una sola vez
    al crear el proyecto (ver proyectos.views.crear_proyecto_view) y no se recalcula."""
    Proyecto = apps.get_model('proyectos', 'Proyecto')
    Profile = apps.get_model('accounts', 'Profile')

    empresa_por_usuario = {
        p.user_id: p.empresa_id
        for p in Profile.objects.filter(empresa__isnull=False)
    }
    for proyecto in Proyecto.objects.filter(creado_por__isnull=False, empresa__isnull=True):
        empresa_id = empresa_por_usuario.get(proyecto.creado_por_id)
        if empresa_id:
            proyecto.empresa_id = empresa_id
            proyecto.save(update_fields=['empresa'])


class Migration(migrations.Migration):

    dependencies = [
        ('proyectos', '0008_proyecto_empresa'),
        ('accounts', '0007_marca'),
    ]

    operations = [
        migrations.RunPython(backfill_empresa, migrations.RunPython.noop),
    ]
