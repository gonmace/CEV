from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('servicios', '0007_add_alcance_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicio',
            name='equipos',
            field=models.JSONField(blank=True, null=True, verbose_name='Equipos'),
        ),
    ]
