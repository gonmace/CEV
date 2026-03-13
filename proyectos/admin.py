from django.contrib import admin
from .models import Proyecto, Especificacion


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'solicitante', 'ubicacion', 'fecha_creacion', 'activo', 'publico')
    list_filter = ('activo', 'publico', 'fecha_creacion')
    search_fields = ('nombre', 'solicitante', 'ubicacion')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')


@admin.register(Especificacion)
class EspecificacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'proyecto', 'especificacion_tecnica', 'fecha_creacion')
    list_filter = ('fecha_creacion', 'proyecto', 'especificacion_tecnica')
    search_fields = ('titulo', 'proyecto__nombre', 'especificacion_tecnica__titulo')
    autocomplete_fields = ('especificacion_tecnica',)

