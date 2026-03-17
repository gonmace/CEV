from django.contrib import admin
from .models import Ubicacion, UbicacionImagen


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'proyecto', 'fecha_creacion', 'cantidad_imagenes')
    list_filter = ('fecha_creacion', 'proyecto')
    search_fields = ('nombre', 'descripcion', 'proyecto__nombre')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    
    def cantidad_imagenes(self, obj):
        return obj.cantidad_imagenes()
    cantidad_imagenes.short_description = 'Imágenes'


@admin.register(UbicacionImagen)
class UbicacionImagenAdmin(admin.ModelAdmin):
    list_display = ('ubicacion', 'imagen', 'fecha_subida')
    list_filter = ('fecha_subida', 'ubicacion__proyecto')
    search_fields = ('ubicacion__nombre', 'descripcion')
    readonly_fields = ('fecha_subida',)

