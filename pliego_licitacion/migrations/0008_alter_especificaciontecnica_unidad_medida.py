# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pliego_licitacion', '0007_especificaciontecnica_unidad_medida'),
    ]

    operations = [
        migrations.AlterField(
            model_name='especificaciontecnica',
            name='unidad_medida',
            field=models.CharField(default='glb', max_length=20, verbose_name='Unidad de Medida'),
        ),
    ]
