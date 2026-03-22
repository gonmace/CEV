import django.db.models.deletion
import servicios.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('servicios', '0001_initial'),
    ]

    operations = [
        # Eliminar modelos antiguos (en orden inverso de dependencias)
        migrations.DeleteModel(name='EspecificacionImagen'),
        migrations.DeleteModel(name='Especificacion'),
        migrations.DeleteModel(name='Proyecto'),

        # Crear nuevo modelo Servicio (standalone)
        migrations.CreateModel(
            name='Servicio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255, verbose_name='Nombre del Servicio')),
                ('solicitante', models.CharField(blank=True, max_length=200, verbose_name='Solicitante')),
                ('contenido', models.TextField(blank=True)),
                ('archivo', models.FileField(blank=True, null=True, upload_to=servicios.models.servicio_upload_path)),
                ('unidad_medida', models.CharField(default='glb', max_length=10, verbose_name='Unidad de Medida')),
                ('cantidad', models.CharField(blank=True, max_length=10, null=True, verbose_name='Cantidad')),
                ('actividades_adicionales', models.JSONField(blank=True, null=True, verbose_name='Actividades Adicionales')),
                ('mostrar', models.BooleanField(default=True, verbose_name='Mostrar')),
                ('orden', models.PositiveIntegerField(db_index=True, default=0)),
                ('publico', models.BooleanField(default=False, verbose_name='Público')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('activo', models.BooleanField(default=True)),
                ('fecha_eliminacion', models.DateTimeField(blank=True, null=True, verbose_name='Fecha de eliminación')),
                ('creado_por', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='servicios_propios',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Servicio',
                'verbose_name_plural': 'Servicios',
                'db_table': 'servicios_servicio',
                'ordering': ['orden', '-fecha_creacion'],
            },
        ),

        # Crear nuevo modelo ServicioImagen
        migrations.CreateModel(
            name='ServicioImagen',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imagen', models.ImageField(upload_to=servicios.models.servicio_imagen_upload_path)),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('fecha_subida', models.DateTimeField(auto_now_add=True)),
                ('servicio', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='imagenes',
                    to='servicios.servicio'
                )),
            ],
            options={
                'verbose_name': 'Imagen de Servicio',
                'verbose_name_plural': 'Imágenes de Servicios',
                'db_table': 'servicios_servicioimagen',
                'ordering': ['-fecha_subida'],
            },
        ),
    ]
