from django.db import migrations, models


def marcar_ya_generados(apps, schema_editor):
    """Los servicios que ya tienen secciones generadas se dan por pagados: son de antes de
    que existieran los créditos, y cobrarlos al regenerarlos sería cobrar dos veces."""
    Servicio = apps.get_model('servicios', 'Servicio')
    Servicio.objects.exclude(secciones_generadas__isnull=True).exclude(
        secciones_generadas='').update(credito_consumido=True)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('servicios', '0009_add_secciones_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicio',
            name='credito_consumido',
            field=models.BooleanField(default=False, verbose_name='Crédito consumido'),
        ),
        migrations.RunPython(marcar_ya_generados, noop),
    ]
