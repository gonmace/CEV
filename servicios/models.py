import os
import logging
from django.db import models, transaction
from django.db.models import Max
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


# Stubs para compatibilidad con migración 0001_initial
def especificacion_upload_path(instance, filename):
    pass

def especificacion_imagen_upload_path(instance, filename):
    pass


class CatalogoServicios(models.Model):
    nombre = models.CharField(max_length=100, default="Catálogo General de Servicios", verbose_name="Nombre")
    datos = models.JSONField(
        default=list,
        verbose_name="Datos del catálogo",
        help_text=(
            "Lista de categorías. Estructura: "
            '[{"nombre": "...", "subcategorias": [{"codigo": "SM-01", "nombre": "...", '
            '"definicion": "...", "alcance": "...", "descripcion": "..."}]}]'
        ),
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'servicios_catalogo'
        verbose_name = "Catálogo de Servicios"
        verbose_name_plural = "Catálogos de Servicios"

    def __str__(self):
        return self.nombre

    @classmethod
    def get_activo(cls):
        return cls.objects.filter(activo=True).first()


def servicio_upload_path(instance, filename):
    slug = slugify(instance.titulo) or 'servicio'
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'servicios/{slug}-{timestamp}.md'


def servicio_imagen_upload_path(instance, filename):
    _, ext = os.path.splitext(filename)
    slug = slugify(instance.servicio.titulo) or 'servicio'
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'servicios/imagenes/{slug}-{timestamp}{ext}'


class Servicio(models.Model):
    categoria_nombre = models.CharField(max_length=255, blank=True, verbose_name="Categoría")
    subcategoria_codigo = models.CharField(max_length=30, blank=True, verbose_name="Código subcategoría")
    subcategoria_nombre = models.CharField(max_length=255, blank=True, verbose_name="Subcategoría")
    titulo = models.CharField(max_length=255, verbose_name="Nombre del Servicio")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    objetivo = models.TextField(blank=True, verbose_name="Objetivo")
    alcance_generado = models.TextField(blank=True, verbose_name="Alcance generado por IA")
    alcance_editado = models.TextField(blank=True, verbose_name="Alcance editado por usuario")
    secciones_generadas = models.TextField(blank=True, verbose_name="Secciones complementarias generadas por IA")
    secciones_editadas = models.TextField(blank=True, verbose_name="Secciones complementarias editadas por usuario")
    solicitante = models.CharField(max_length=200, verbose_name="Solicitante", blank=True)
    contenido = models.TextField(blank=True)
    archivo = models.FileField(upload_to=servicio_upload_path, blank=True, null=True)
    unidad_medida = models.CharField(max_length=10, verbose_name='Unidad de Medida', default='glb')
    cantidad = models.CharField(max_length=10, verbose_name='Cantidad', blank=True, null=True)
    actividades_adicionales = models.JSONField(verbose_name='Actividades Adicionales', blank=True, null=True)
    equipos = models.JSONField(verbose_name='Equipos', blank=True, null=True)
    mostrar = models.BooleanField(default=True, verbose_name='Mostrar')
    orden = models.PositiveIntegerField(default=0, db_index=True)
    publico = models.BooleanField(default=False, verbose_name="Público")
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='servicios_propios'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    fecha_eliminacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de eliminación")

    class Meta:
        db_table = 'servicios_servicio'
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        ordering = ['orden', '-fecha_creacion']

    def save(self, *args, **kwargs):
        if self.pk is None and self.orden == 0:
            with transaction.atomic():
                max_orden = Servicio.objects.select_for_update().filter(activo=True).aggregate(
                    max_orden=Max('orden')
                )['max_orden'] or 0
                self.orden = max_orden + 1
                super().save(*args, **kwargs)
                return
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo

    def tiene_imagenes(self):
        return self.imagenes.exists()

    def cantidad_imagenes(self):
        return self.imagenes.count()


class ServicioImagen(models.Model):
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        related_name='imagenes'
    )
    imagen = models.ImageField(upload_to=servicio_imagen_upload_path)
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'servicios_servicioimagen'
        ordering = ['-fecha_subida']
        verbose_name = "Imagen de Servicio"
        verbose_name_plural = "Imágenes de Servicios"

    def save(self, *args, **kwargs):
        if self.imagen and (not self.pk or 'imagen' in kwargs.get('update_fields', [])):
            try:
                img = Image.open(self.imagen)
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                max_size = 1920
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                output = BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                output.seek(0)
                original_name = os.path.splitext(self.imagen.name)[0]
                self.imagen.save(f"{original_name}.jpg", ContentFile(output.read()), save=False)
            except Exception as e:
                logger.warning(f"Error al optimizar imagen: {e}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Imagen de {self.servicio.titulo}"
