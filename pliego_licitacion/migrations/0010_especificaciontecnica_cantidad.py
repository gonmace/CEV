# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pliego_licitacion', '0009_alter_especificaciontecnica_unidad_medida_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='especificaciontecnica',
            name='cantidad',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Cantidad'),
        ),
    ]
