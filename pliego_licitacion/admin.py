from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import markdown
import re
from .models import EspecificacionTecnica, Parametros, ActividadesAdicionales


class ParametrosInline(admin.TabularInline):
    """Inline para mostrar parámetros relacionados con la especificación técnica"""
    model = Parametros
    extra = 0
    fields = ('parametro', 'valor', 'unidad', 'detalle')
    verbose_name = 'Parámetro'
    verbose_name_plural = 'Parámetros Técnicos'


class ActividadesAdicionalesInline(admin.TabularInline):
    """Inline para mostrar actividades adicionales relacionadas con la especificación técnica"""
    model = ActividadesAdicionales
    extra = 0
    fields = ('nombre', 'valor_recomendado', 'unidad_medida', 'descripcion')
    verbose_name = 'Actividad Adicional'
    verbose_name_plural = 'Actividades Adicionales'


@admin.register(EspecificacionTecnica)
class EspecificacionTecnicaAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'tipo_servicio', 'descripcion', 'resultado_markdown_preview', 'creado_por')
    list_filter = ('tipo_servicio', 'fecha_creacion', 'creado_por')
    search_fields = ('titulo', 'descripcion')
    readonly_fields = ('id', 'resultado_markdown_preview', 'resultado_markdown_html', 'fecha_creacion', 'fecha_actualizacion')
    list_per_page = 25
    date_hierarchy = 'fecha_creacion'
    inlines = [ParametrosInline, ActividadesAdicionalesInline]
    
    fieldsets = (
        ('Información Principal', {
            'fields': ('id', 'titulo', 'descripcion', 'tipo_servicio')
        }),
        ('Medidas', {
            'fields': ('unidad_medida', 'cantidad')
        }),
        ('Resultado', {
            'fields': ('resultado_markdown_preview', 'resultado_markdown_html')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def resultado_markdown_preview(self, obj):
        """
        Muestra solo las primeras 20 palabras del resultado_markdown
        """
        if not obj.resultado_markdown:
            return '-'
        
        # Limpiar el texto de markdown básico (remover #, *, etc.)
        texto = obj.resultado_markdown
        # Remover encabezados markdown
        texto = texto.replace('#', '')
        # Remover listas markdown
        texto = texto.replace('*', '')
        texto = texto.replace('-', '')
        # Remover saltos de línea múltiples y espacios extra
        texto = ' '.join(texto.split())
        
        # Obtener las primeras 20 palabras
        palabras = texto.split()[:20]
        preview = ' '.join(palabras)
        
        # Agregar "..." si hay más texto
        if len(texto.split()) > 20:
            preview += '...'
        
        return preview
    
    resultado_markdown_preview.short_description = 'Resultado (Primeras 20 palabras)'
    
    def resultado_markdown_html(self, obj):
        """
        Renderiza el resultado_markdown como HTML, limpiando los delimitadores ```markdown
        """
        if not obj.resultado_markdown:
            return '-'
        
        # Limpiar el texto: remover delimitadores ```markdown y ```
        texto = obj.resultado_markdown
        
        # Remover delimitadores de código markdown al inicio y final
        # Patrón para ```markdown al inicio y ``` al final
        texto = re.sub(r'^```markdown\s*', '', texto, flags=re.MULTILINE)
        texto = re.sub(r'\s*```\s*$', '', texto, flags=re.MULTILINE)
        
        # También remover si están en líneas separadas
        texto = re.sub(r'^```markdown\s*\n', '', texto, flags=re.MULTILINE)
        texto = re.sub(r'\n\s*```\s*$', '', texto, flags=re.MULTILINE)
        
        # Limpiar espacios en blanco al inicio y final
        texto = texto.strip()
        
        # Convertir markdown a HTML
        extensions = [
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.tables',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists'
        ]
        
        try:
            html = markdown.markdown(texto, output_format='html', extensions=extensions)
            # Usar mark_safe para permitir que Django renderice el HTML
            return format_html('<div style="max-width: 100%; overflow-x: auto;">{}</div>', mark_safe(html))
        except Exception as e:
            # Si hay error al convertir, mostrar el texto original escapado
            return format_html('<pre style="white-space: pre-wrap;">{}</pre>', texto)
    
    resultado_markdown_html.short_description = 'Resultado (HTML Renderizado)'


@admin.register(Parametros)
class ParametrosAdmin(admin.ModelAdmin):
    list_display = ('id', 'parametro', 'valor', 'unidad', 'especificacion_tecnica')
    list_filter = ('especificacion_tecnica',)
    search_fields = ('parametro', 'valor', 'detalle')
    readonly_fields = ('id',)
    list_per_page = 25
    
    fieldsets = (
        ('Información del Parámetro', {
            'fields': ('parametro', 'valor', 'unidad', 'detalle')
        }),
        ('Relación', {
            'fields': ('especificacion_tecnica', 'id')
        }),
    )


@admin.register(ActividadesAdicionales)
class ActividadesAdicionalesAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'valor_recomendado', 'unidad_medida', 'especificacion_tecnica')
    list_filter = ('especificacion_tecnica',)
    search_fields = ('nombre', 'valor_recomendado', 'descripcion')
    readonly_fields = ('id',)
    list_per_page = 25
    
    fieldsets = (
        ('Información de la Actividad', {
            'fields': ('nombre', 'valor_recomendado', 'unidad_medida', 'descripcion')
        }),
        ('Relación', {
            'fields': ('especificacion_tecnica', 'id')
        }),
    )








