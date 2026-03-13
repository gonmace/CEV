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
    cantidad = models.CharField(
        max_length=10,
        verbose_name='Cantidad',
        blank=True,
        null=True
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
    resultado_markdown = models.TextField(verbose_name='Resultado en Markdown', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Especificación Técnica'
        verbose_name_plural = 'Especificaciones Técnicas'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.titulo} - {self.tipo_servicio}"


class Parametros(models.Model):
    """
    Modelo para almacenar los parámetros técnicos asociados a una especificación técnica
    """
    especificacion_tecnica = models.ForeignKey(
        EspecificacionTecnica,
        on_delete=models.CASCADE,
        related_name='parametros',
        verbose_name='Especificación Técnica'
    )
    parametro = models.CharField(max_length=255, verbose_name='Parámetro')
    valor = models.CharField(max_length=255, verbose_name='Valor Recomendado', blank=True, null=True)
    unidad = models.CharField(max_length=50, verbose_name='Unidad de Medida', blank=True, null=True)
    detalle = models.TextField(verbose_name='Detalle', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Parámetro'
        verbose_name_plural = 'Parámetros'
        ordering = ['parametro']
    
    def __str__(self):
        return f"{self.parametro} - {self.especificacion_tecnica.titulo}"


class ActividadesAdicionales(models.Model):
    """
    Modelo para almacenar las actividades adicionales asociadas a una especificación técnica
    """
    especificacion_tecnica = models.ForeignKey(
        EspecificacionTecnica,
        on_delete=models.CASCADE,
        related_name='actividades_adicionales',
        verbose_name='Especificación Técnica'
    )
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    valor_recomendado = models.CharField(max_length=255, verbose_name='Valor Recomendado', blank=True, null=True)
    unidad_medida = models.CharField(max_length=50, verbose_name='Unidad de Medida', blank=True, null=True)
    descripcion = models.TextField(verbose_name='Descripción', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Actividad Adicional'
        verbose_name_plural = 'Actividades Adicionales'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} - {self.especificacion_tecnica.titulo}"
