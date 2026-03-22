import django.db.models.deletion
from django.db import migrations, models


def crear_catalogo_y_migrar(apps, schema_editor):
    CatalogoServicios = apps.get_model('servicios', 'CatalogoServicios')
    Categoria = apps.get_model('servicios', 'Categoria')
    Servicio = apps.get_model('servicios', 'Servicio')

    # Construir catálogo desde datos existentes (sin definicion/alcance aún)
    datos = []
    for cat in Categoria.objects.prefetch_related('subcategorias').order_by('orden'):
        datos.append({
            'nombre': cat.nombre,
            'subcategorias': [
                {
                    'codigo': sub.codigo,
                    'nombre': sub.nombre,
                    'definicion': '',
                    'alcance': '',
                    'descripcion': '',
                }
                for sub in cat.subcategorias.order_by('orden')
            ],
        })

    CatalogoServicios.objects.create(nombre='Catálogo General de Servicios', datos=datos)

    # Migrar datos de FK a campos de texto en Servicio
    for s in Servicio.objects.filter(activo=True).select_related('subcategoria', 'subcategoria__categoria'):
        if s.subcategoria_id:
            sub = s.subcategoria
            s.subcategoria_codigo = sub.codigo
            s.subcategoria_nombre = sub.nombre
            s.categoria_nombre = sub.categoria.nombre
            s.save(update_fields=['subcategoria_codigo', 'subcategoria_nombre', 'categoria_nombre'])


def revertir_catalogo(apps, schema_editor):
    CatalogoServicios = apps.get_model('servicios', 'CatalogoServicios')
    CatalogoServicios.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('servicios', '0005_servicio_objetivo'),
    ]

    operations = [
        # 1. Crear modelo CatalogoServicios
        migrations.CreateModel(
            name='CatalogoServicios',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(default='Catálogo General de Servicios', max_length=100, verbose_name='Nombre')),
                ('datos', models.JSONField(default=list, verbose_name='Datos del catálogo')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Catálogo de Servicios',
                'verbose_name_plural': 'Catálogos de Servicios',
                'db_table': 'servicios_catalogo',
            },
        ),

        # 2. Agregar nuevos campos de texto a Servicio
        migrations.AddField(
            model_name='servicio',
            name='categoria_nombre',
            field=models.CharField(blank=True, max_length=255, verbose_name='Categoría'),
        ),
        migrations.AddField(
            model_name='servicio',
            name='subcategoria_codigo',
            field=models.CharField(blank=True, max_length=30, verbose_name='Código subcategoría'),
        ),
        migrations.AddField(
            model_name='servicio',
            name='subcategoria_nombre',
            field=models.CharField(blank=True, max_length=255, verbose_name='Subcategoría'),
        ),

        # 3. Data migration: crear catálogo y migrar datos
        migrations.RunPython(crear_catalogo_y_migrar, revertir_catalogo),

        # 4. Eliminar FK de Servicio a Subcategoria
        migrations.RemoveField(
            model_name='servicio',
            name='subcategoria',
        ),

        # 5. Eliminar tablas Subcategoria y Categoria
        migrations.DeleteModel(name='Subcategoria'),
        migrations.DeleteModel(name='Categoria'),
    ]
