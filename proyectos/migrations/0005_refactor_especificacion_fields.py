from django.db import migrations, models


def copiar_actividades_adicionales(apps, schema_editor):
    """
    Copia actividades_adicionales desde EspecificacionTecnica a Especificacion
    para todos los registros existentes que tengan la FK.
    """
    Especificacion = apps.get_model('proyectos', 'Especificacion')
    for esp in Especificacion.objects.select_related('especificacion_tecnica').filter(
        especificacion_tecnica__isnull=False
    ):
        et = esp.especificacion_tecnica
        if et and et.actividades_adicionales:
            esp.actividades_adicionales = et.actividades_adicionales
            esp.save(update_fields=['actividades_adicionales'])


class Migration(migrations.Migration):

    dependencies = [
        ('proyectos', '0004_add_cantidad_to_especificacion'),
        ('pliego_licitacion', '0020_remove_cantidad_from_especificacion_tecnica'),
    ]

    operations = [
        # 1. Agregar nuevo campo
        migrations.AddField(
            model_name='especificacion',
            name='actividades_adicionales',
            field=models.JSONField(blank=True, null=True, verbose_name='Actividades Adicionales'),
        ),
        # 2. Migrar datos existentes
        migrations.RunPython(copiar_actividades_adicionales, migrations.RunPython.noop),
        # 3. Eliminar token_cost
        migrations.RemoveField(
            model_name='especificacion',
            name='token_cost',
        ),
        # 4. Eliminar especificacion_tecnica FK
        migrations.RemoveField(
            model_name='especificacion',
            name='especificacion_tecnica',
        ),
    ]
