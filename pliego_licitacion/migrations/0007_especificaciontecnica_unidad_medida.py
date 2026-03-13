# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pliego_licitacion', '0006_remove_actividadesadicionales_sessionid_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='especificaciontecnica',
            name='unidad_medida',
            field=models.CharField(default='glb', max_length=20, verbose_name='Unidad de Medida'),
        ),
    ]
