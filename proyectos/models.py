import os
from django.db import models
from django.db.models import Max
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile


class Proyecto(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre de Proyecto")
    solicitante = models.CharField(max_length=200, verbose_name="Solicitante")
    ubicacion = models.CharField(max_length=200, verbose_name="Ubicación")
    descripcion = models.TextField(verbose_name="Descripción", blank=True)
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    fecha_eliminacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de eliminación")
    publico = models.BooleanField(default=False, verbose_name="Público")

    class Meta:
        db_table = 'main_proyecto'
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.nombre


def especificacion_upload_path(instance, filename):
    base, ext = os.path.splitext(filename)
    slug = slugify(instance.titulo) or 'especificacion'
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'especificaciones/{instance.proyecto_id}/{slug}-{timestamp}.md'


def especificacion_imagen_upload_path(instance, filename):
    base, ext = os.path.splitext(filename)
    slug = slugify(instance.especificacion.titulo) or 'especificacion'
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'especificaciones/{instance.especificacion.proyecto_id}/imagenes/{slug}-{timestamp}{ext}'


class Especificacion(models.Model):
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='especificaciones'
    )
    titulo = models.CharField(max_length=255)
    contenido = models.TextField(blank=True)
    archivo = models.FileField(upload_to=especificacion_upload_path, blank=True, null=True)
    unidad_medida = models.CharField(max_length=10, verbose_name='Unidad de Medida', default='glb')
    cantidad = models.CharField(max_length=10, verbose_name='Cantidad', blank=True, null=True)
    actividades_adicionales = models.JSONField(verbose_name='Actividades Adicionales', blank=True, null=True)
    mostrar = models.BooleanField(default=True, verbose_name='Mostrar')
    orden = models.PositiveIntegerField(default=0, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'main_especificacion'
        ordering = ['orden', '-fecha_creacion']

    def save(self, *args, **kwargs):
        # Si es una nueva especificación y no tiene orden asignado, asignar el siguiente orden disponible
        if self.pk is None and self.orden == 0:
            max_orden = Especificacion.objects.filter(proyecto=self.proyecto).aggregate(
                max_orden=Max('orden')
            )['max_orden'] or 0
            self.orden = max_orden + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titulo} ({self.proyecto.nombre})"
    
    def tiene_imagenes(self):
        """Verifica si la especificación tiene imágenes asociadas"""
        return self.imagenes.exists()
    
    def cantidad_imagenes(self):
        """Retorna la cantidad de imágenes asociadas"""
        return self.imagenes.count()


class EspecificacionImagen(models.Model):
    especificacion = models.ForeignKey(
        Especificacion,
        on_delete=models.CASCADE,
        related_name='imagenes'
    )
    imagen = models.ImageField(upload_to=especificacion_imagen_upload_path)
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    fecha_subida = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'main_especificacionimagen'
        ordering = ['-fecha_subida']
        verbose_name = "Imagen de Especificación"
        verbose_name_plural = "Imágenes de Especificaciones"
    
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
                print(f"Error al optimizar imagen: {e}")
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Imagen de {self.especificacion.titulo}"

