# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proyectos', '0001_initial'),
        ('pliego_licitacion', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='especificacion',
            name='especificacion_tecnica',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='especificaciones',
                to='pliego_licitacion.especificaciontecnica',
                verbose_name='Especificación Técnica'
            ),
        ),
    ]

