import django.db.models.deletion
import ubi_web.models
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('proyectos', '0006_add_mostrar_to_especificacion'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ubicacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255, verbose_name='Nombre de la Ubicación')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('contenido', models.TextField(blank=True, help_text='Contenido en formato Markdown para el documento PDF', verbose_name='Contenido (Markdown)')),
                ('latitud', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='Latitud')),
                ('longitud', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='Longitud')),
                ('ciudad', models.CharField(blank=True, max_length=255, verbose_name='Ciudad')),
                ('documento_pdf', models.FileField(blank=True, null=True, upload_to='ubicaciones/documentos/', verbose_name='Documento PDF')),
                ('mapa_imagen', models.ImageField(blank=True, null=True, upload_to='ubicaciones/mapas/', verbose_name='Mapa')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('proyecto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ubicaciones', to='proyectos.proyecto')),
            ],
            options={
                'verbose_name': 'Ubicación',
                'verbose_name_plural': 'Ubicaciones',
                'ordering': ['-fecha_creacion'],
            },
        ),
        migrations.CreateModel(
            name='UbicacionImagen',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imagen', models.ImageField(upload_to=ubi_web.models.ubicacion_imagen_upload_path)),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('fecha_subida', models.DateTimeField(auto_now_add=True)),
                ('ubicacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='imagenes', to='ubi_web.ubicacion')),
            ],
            options={
                'verbose_name': 'Imagen de Ubicación',
                'verbose_name_plural': 'Imágenes de Ubicaciones',
                'ordering': ['-fecha_subida'],
            },
        ),
    ]
