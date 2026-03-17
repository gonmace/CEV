from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pliego_licitacion', '0018_add_eliminado_paso'),
        ('proyectos', '0003_especificacion_unidad_medida'),
    ]

    operations = [
        migrations.AddField(
            model_name='especificaciontecnica',
            name='proyecto',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='especificaciones_tecnicas',
                to='proyectos.proyecto',
                verbose_name='Proyecto',
            ),
        ),
    ]
