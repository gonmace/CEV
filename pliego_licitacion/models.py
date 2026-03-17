from django.db import models
from django.contrib.auth.models import User


class EspecificacionTecnica(models.Model):
    """
    Modelo general para almacenar las especificaciones técnicas generadas
    """
    titulo = models.CharField(max_length=100, verbose_name='Título')
    descripcion = models.TextField(verbose_name='Descripción')
    tipo_servicio = models.CharField(
        max_length=100,
        verbose_name='Tipo de Servicio',
        choices=[
            ('Mecánico', 'Mecánico'),
            ('Eléctrico', 'Eléctrico'),
            ('Instrumentación', 'Instrumentación'),
            ('SSMA', 'SSMA (Seguridad, Salud y Medio Ambiente)'),
            ('Infraestructura / Obras Civiles', 'Infraestructura / Obras Civiles (OOCC)'),
            ('Mantenimiento de Vehículos', 'Mantenimiento de Vehículos'),
            ('Laboratorio y Aseguramiento de la Calidad', 'Laboratorio y Aseguramiento de la Calidad'),
            ('Logística y Distribución', 'Logística y Distribución'),
        ]
    )
    unidad_medida = models.CharField(
        max_length=10,
        verbose_name='Unidad de Medida',
        default='glb'
    )
    proyecto = models.ForeignKey(
        'proyectos.Proyecto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='especificaciones_tecnicas',
        verbose_name='Proyecto'
    )
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='especificaciones_tecnicas_creadas',
        verbose_name='Creado por'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')
    clasificacion = models.JSONField(verbose_name='Clasificación', blank=True, null=True)
    parametros_materiales = models.JSONField(verbose_name='Parámetros Materiales', blank=True, null=True)
    parametros_ejecucion = models.JSONField(verbose_name='Parámetros Ejecución', blank=True, null=True)
    normas_aplicables = models.JSONField(verbose_name='Normas Aplicables', blank=True, null=True)
    criterios_calidad = models.JSONField(verbose_name='Criterios de Calidad', blank=True, null=True)
    actividades_adicionales = models.JSONField(verbose_name='Actividades Adicionales', blank=True, null=True)
    resumen = models.TextField(verbose_name='Resumen', blank=True, null=True)
    resultado_markdown = models.TextField(verbose_name='Resultado en Markdown', blank=True, null=True)
    eliminado = models.BooleanField(default=False, verbose_name='Eliminado')
    paso = models.IntegerField(default=0, verbose_name='Paso')

    class Meta:
        verbose_name = 'Especificación Técnica'
        verbose_name_plural = 'Especificaciones Técnicas'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.titulo} - {self.tipo_servicio}"
