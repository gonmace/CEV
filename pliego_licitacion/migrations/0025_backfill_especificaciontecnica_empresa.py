from django.db import migrations


def backfill_empresa(apps, schema_editor):
    """Fija EspecificacionTecnica.empresa según la empresa que tenía `creado_por` en
    este momento — best-effort para los datos históricos. De acá en más el campo se
    fija una sola vez al crear el borrador (ver pliego_licitacion.views) y no se
    recalcula."""
    EspecificacionTecnica = apps.get_model('pliego_licitacion', 'EspecificacionTecnica')
    Profile = apps.get_model('accounts', 'Profile')

    empresa_por_usuario = {
        p.user_id: p.empresa_id
        for p in Profile.objects.filter(empresa__isnull=False)
    }
    for et in EspecificacionTecnica.objects.filter(creado_por__isnull=False, empresa__isnull=True):
        empresa_id = empresa_por_usuario.get(et.creado_por_id)
        if empresa_id:
            et.empresa_id = empresa_id
            et.save(update_fields=['empresa'])


class Migration(migrations.Migration):

    dependencies = [
        ('pliego_licitacion', '0024_especificaciontecnica_empresa'),
        ('accounts', '0007_marca'),
    ]

    operations = [
        migrations.RunPython(backfill_empresa, migrations.RunPython.noop),
    ]
