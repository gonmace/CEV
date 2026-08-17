from django.db import migrations, models


def marcar_ya_generados(apps, schema_editor):
    """Los pliegos que ya existen se dan por pagados.

    Se generaron antes de que existieran los créditos, así que cobrarlos ahora (la primera
    vez que alguien los regenere) sería cobrar dos veces por el mismo entregable.
    """
    EspecificacionTecnica = apps.get_model('pliego_licitacion', 'EspecificacionTecnica')
    EspecificacionTecnica.objects.exclude(resultado_markdown__isnull=True).exclude(
        resultado_markdown='').update(credito_consumido=True)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pliego_licitacion', '0022_remove_especificaciontecnica_es_demo'),
    ]

    operations = [
        migrations.AddField(
            model_name='especificaciontecnica',
            name='credito_consumido',
            field=models.BooleanField(default=False, verbose_name='Crédito consumido'),
        ),
        migrations.RunPython(marcar_ya_generados, noop),
    ]
