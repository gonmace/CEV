from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('servicios', '0008_servicio_equipos'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicio',
            name='secciones_generadas',
            field=models.TextField(blank=True, verbose_name='Secciones complementarias generadas por IA'),
        ),
        migrations.AddField(
            model_name='servicio',
            name='secciones_editadas',
            field=models.TextField(blank=True, verbose_name='Secciones complementarias editadas por usuario'),
        ),
    ]
