import django.db.models.deletion
from django.db import migrations, models


CATEGORIAS_DATA = [
    {
        'nombre': 'SERVICIOS MECÁNICOS',
        'subcategorias': [
            ('SM-01', 'Mantenimiento Predictivo – Análisis Vibracional'),
            ('SM-02', 'Mantenimiento Predictivo – Análisis de Aceite'),
            ('SM-03', 'Mantenimiento Predictivo – Ultrasonido'),
            ('SM-04', 'Mantenimiento Preventivo – Equipos Industriales'),
            ('SM-05', 'Mantenimiento Preventivo – Sistemas Mecánicos'),
            ('SM-06', 'Mantenimiento Correctivo – Equipos Industriales'),
            ('SM-07', 'Mantenimiento Correctivo – Sistemas Mecánicos'),
            ('SM-08', 'Fabricación y Recuperación de Piezas'),
            ('SM-09', 'Soldadura Industrial (MIG, TIG, Arco Eléctrico)'),
            ('SM-10', 'Mecanizado Convencional – Torno, Fresa, Taladro'),
            ('SM-11', 'Mano de Obra Técnica Mecánica'),
            ('SM-12', 'Alineación de Equipos (Láser, Reloj Comparador)'),
            ('SM-13', 'Montaje y Desmontaje de Sistemas Mecánicos'),
            ('SM-14', 'Mantenimiento de Racks de Almacenamiento'),
            ('SM-15', 'Ajuste y Puesta en Marcha de Equipos Industriales'),
            ('SM-16', 'Mantenimiento de Equipos de Frío Comerciales'),
        ],
    },
    {
        'nombre': 'SERVICIOS ELÉCTRICOS',
        'subcategorias': [
            ('SE-01', 'Mantenimiento Predictivo – Termografía'),
            ('SE-02', 'Mantenimiento Predictivo – Ultrasonido'),
            ('SE-03', 'Mantenimiento Preventivo – Equipos Industriales'),
            ('SE-04', 'Mantenimiento Correctivo – Equipos Industriales'),
            ('SE-05', 'Mantenimiento Preventivo – Sistemas Eléctricos'),
            ('SE-06', 'Mano de Obra Técnica Eléctrica'),
            ('SE-07', 'Instalaciones Eléctricas Industriales'),
            ('SE-08', 'Instalaciones Eléctricas Menores'),
            ('SE-09', 'Rebobinado de Motores'),
            ('SE-10', 'Mantenimiento Preventivo de Aires Acondicionados'),
            ('SE-11', 'Mantenimiento de Codificadores'),
            ('SE-12', 'Medición y Verificación de Puesta a Tierra y Pararrayos'),
        ],
    },
    {
        'nombre': 'SERVICIOS INSTRUMENTACIÓN',
        'subcategorias': [
            ('SI-01', 'Calibración de Válvulas de Seguridad'),
            ('SI-02', 'Calibración de Instrumentos en Línea'),
            ('SI-03', 'Calibración de Sensores de Gases'),
            ('SI-04', 'Calibración de Instrumentación General'),
            ('SI-05', 'Calibración de Patrones'),
            ('SI-06', 'Mantenimiento de Sistemas de Control'),
            ('SI-07', 'Mantenimiento de Servomotores y Actuadores Electrónicos'),
        ],
    },
    {
        'nombre': 'SERVICIOS SSMA',
        'subcategorias': [
            ('SSMA-01', 'Prevención y Extinción de Incendios'),
            ('SSMA-02', 'Tratamiento de Residuos Industriales'),
            ('SSMA-03', 'Servicios de Prevencionistas SSMA'),
            ('SSMA-04', 'Servicios de Gestión de Medio Ambiente'),
            ('SSMA-05', 'Monitoreo Ambiental (Agua, Ruido, Gases)'),
            ('SSMA-06', 'Servicio de Certificación de Equipos de Riesgo Crítico'),
            ('SSMA-07', 'Cálculo de Carga Estructural de Plataformas'),
            ('SSMA-08', 'Servicio de Alquiler de Equipos de Seguridad'),
        ],
    },
    {
        'nombre': 'SERVICIOS INFRAESTRUCTURA OOCC',
        'subcategorias': [
            ('SINFRA-01', 'Mantenimiento y Cambio de Filtros – Presión Positiva'),
            ('SINFRA-02', 'Reparación de Fachadas – Revoque Interior y Exterior'),
            ('SINFRA-03', 'Reparación de Oficinas y Áreas Comunes'),
            ('SINFRA-04', 'Pintura Interior, Exterior y de Pisos'),
            ('SINFRA-05', 'Reparación de Pisos y Zócalos'),
            ('SINFRA-06', 'Cambio de Vidrios'),
            ('SINFRA-07', 'Mantenimiento de Puertas, Cerraduras y Brazos Hidráulicos'),
            ('SINFRA-08', 'Servicios de Drenaje y Canalización'),
            ('SINFRA-09', 'Servicios de Plomería en General'),
            ('SINFRA-10', 'Limpieza de Cámaras y Canales Industriales'),
            ('SINFRA-11', 'Reposición y Arreglo de Cubiertas (Techos) Plásticas y Galvanizadas'),
        ],
    },
    {
        'nombre': 'SERVICIOS MANTENIMIENTO VEHÍCULOS',
        'subcategorias': [
            ('VEH-01', 'Mantenimiento Preventivo de Equipo Pesado'),
            ('VEH-02', 'Mantenimiento Preventivo de Vehículos'),
            ('VEH-03', 'Mantenimiento Correctivo de Equipo Pesado con Provisión de Repuestos'),
            ('VEH-04', 'Mantenimiento Correctivo de Vehículos con Provisión de Repuestos'),
            ('VEH-05', 'Provisión de Tanques de GNV'),
        ],
    },
    {
        'nombre': 'SERVICIOS LABORATORIO Y ASEGURAMIENTO DE CALIDAD',
        'subcategorias': [
            ('LAB-01', 'Calibración de Instrumentos de Laboratorio'),
            ('LAB-02', 'Análisis Físico-Químico'),
            ('LAB-03', 'Análisis Microbiológico'),
            ('LAB-04', 'Mantenimiento de Equipos de Laboratorio'),
            ('LAB-07', 'Servicios de Inocuidad'),
            ('LAB-09', 'Control de Plagas'),
        ],
    },
    {
        'nombre': 'SERVICIOS LOGÍSTICA Y DISTRIBUCIÓN',
        'subcategorias': [
            ('LOG-01', 'Alquiler de Equipos Pesados (de varias Tn)'),
            ('LOG-02', 'Descarte de Producto No Conforme (PNC)'),
            ('LOG-03', 'Servicio de Apoyo Logístico'),
        ],
    },
]


def poblar_categorias(apps, schema_editor):
    Categoria = apps.get_model('servicios', 'Categoria')
    Subcategoria = apps.get_model('servicios', 'Subcategoria')
    for orden_cat, cat_data in enumerate(CATEGORIAS_DATA, start=1):
        cat = Categoria.objects.create(nombre=cat_data['nombre'], orden=orden_cat)
        for orden_sub, (codigo, nombre) in enumerate(cat_data['subcategorias'], start=1):
            Subcategoria.objects.create(
                categoria=cat,
                codigo=codigo,
                nombre=nombre,
                orden=orden_sub
            )


def limpiar_categorias(apps, schema_editor):
    Categoria = apps.get_model('servicios', 'Categoria')
    Categoria.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('servicios', '0002_refactor_to_servicio'),
    ]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, verbose_name='Categoría')),
                ('orden', models.PositiveIntegerField(db_index=True, default=0)),
            ],
            options={
                'verbose_name': 'Categoría',
                'verbose_name_plural': 'Categorías',
                'db_table': 'servicios_categoria',
                'ordering': ['orden', 'nombre'],
            },
        ),
        migrations.CreateModel(
            name='Subcategoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=20, unique=True, verbose_name='Código')),
                ('nombre', models.CharField(max_length=255, verbose_name='Nombre')),
                ('orden', models.PositiveIntegerField(db_index=True, default=0)),
                ('categoria', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subcategorias',
                    to='servicios.categoria'
                )),
            ],
            options={
                'verbose_name': 'Subcategoría',
                'verbose_name_plural': 'Subcategorías',
                'db_table': 'servicios_subcategoria',
                'ordering': ['categoria__orden', 'orden', 'codigo'],
            },
        ),
        migrations.AddField(
            model_name='servicio',
            name='subcategoria',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='servicios',
                to='servicios.subcategoria',
                verbose_name='Subcategoría'
            ),
        ),
        migrations.RunPython(poblar_categorias, limpiar_categorias),
    ]
