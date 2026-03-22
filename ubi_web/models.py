import os
import logging
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
from proyectos.models import Proyecto

logger = logging.getLogger(__name__)


def ubicacion_imagen_upload_path(instance, filename):
    base, ext = os.path.splitext(filename)
    slug = slugify(instance.ubicacion.nombre) or 'ubicacion'
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'ubicaciones/{instance.ubicacion.proyecto_id}/imagenes/{slug}-{timestamp}{ext}'


class Ubicacion(models.Model):
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='ubicaciones'
    )
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la Ubicación")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    contenido = models.TextField(blank=True, verbose_name="Contenido (Markdown)", help_text="Contenido en formato Markdown para el documento PDF")
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Latitud")
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Longitud")
    ciudad = models.CharField(max_length=255, verbose_name="Ciudad/Localidad")
    documento_pdf = models.FileField(upload_to='ubicaciones/documentos/', blank=True, null=True, verbose_name="Documento PDF")
    mapa_imagen = models.ImageField(upload_to='ubicaciones/mapas/', blank=True, null=True, verbose_name="Mapa")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.nombre} ({self.proyecto.nombre})"
    
    def tiene_imagenes(self):
        """Verifica si la ubicación tiene imágenes asociadas"""
        return self.imagenes.exists()
    
    def cantidad_imagenes(self):
        """Retorna la cantidad de imágenes asociadas"""
        return self.imagenes.count()


class UbicacionImagen(models.Model):
    ubicacion = models.ForeignKey(
        Ubicacion,
        on_delete=models.CASCADE,
        related_name='imagenes'
    )
    imagen = models.ImageField(upload_to=ubicacion_imagen_upload_path)
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    fecha_subida = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = "Imagen de Ubicación"
        verbose_name_plural = "Imágenes de Ubicaciones"
    
    def save(self, *args, **kwargs):
        # Optimizar la imagen antes de guardar (solo si es nueva o se está actualizando)
        if self.imagen and (not self.pk or 'imagen' in kwargs.get('update_fields', [])):
            try:
                img = Image.open(self.imagen)
                
                # Convertir a RGB si es necesario (para JPEG)
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Redimensionar si es muy grande (máximo 1920px en el lado más largo)
                max_size = 1920
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Guardar optimizada
                output = BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                output.seek(0)
                
                # Obtener el nombre del archivo original y cambiar la extensión a .jpg
                original_name = os.path.splitext(self.imagen.name)[0]
                new_filename = f"{original_name}.jpg"
                
                # Reemplazar el archivo original con el optimizado
                self.imagen.save(
                    new_filename,
                    ContentFile(output.read()),
                    save=False
                )
            except Exception as e:
                # Si hay un error al optimizar, continuar con el guardado normal
                logger.warning(f"Error al optimizar imagen: {e}")
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Imagen de {self.ubicacion.nombre}"
