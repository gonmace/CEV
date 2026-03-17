from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import markdown
import re
from .models import EspecificacionTecnica


def _tabla_parametros(datos, columnas):
    """
    Renderiza una lista de dicts como tabla HTML para el admin.
    `columnas` es una lista de (key, label).
    """
    if not datos:
        return mark_safe('<span style="color:#aaa;">—</span>')

    th = ''.join(
        f'<th style="padding:6px 12px;text-align:left;background:#3c5a8a;color:#ffffff;'
        f'border-bottom:2px solid #2a3f63;white-space:nowrap;">{label}</th>'
        for _, label in columnas
    )
    filas = []
    for i, fila in enumerate(datos):
        bg = '#ffffff' if i % 2 == 0 else '#eef2f7'
        celdas = ''
        for key, _ in columnas:
            valor = fila.get(key, '') or ''
            celdas += (
                f'<td style="padding:6px 12px;vertical-align:top;color:#1a1a2e;'
                f'border-bottom:1px solid #d0d7e3;">{valor}</td>'
            )
        filas.append(f'<tr style="background:{bg};">{celdas}</tr>')

    rows_html = ''.join(filas)
    return mark_safe(
        f'<div style="overflow-x:auto;">'
        f'<table style="border-collapse:collapse;width:100%;font-size:13px;">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>'
    )


@admin.register(EspecificacionTecnica)
class EspecificacionTecnicaAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'tipo_servicio', 'descripcion_corta', 'paso', 'tiene_resultado', 'eliminado', 'proyecto', 'creado_por', 'fecha_creacion')
    list_filter = ('tipo_servicio', 'eliminado', 'fecha_creacion', 'creado_por', 'proyecto')
    search_fields = ('titulo', 'descripcion')
    readonly_fields = (
        'id',
        'clasificacion',
        'tabla_parametros_materiales',
        'tabla_parametros_ejecucion',
        'tabla_normas_aplicables',
        'tabla_criterios_calidad',
        'tabla_actividades_adicionales',
        'resumen',
        'resultado_markdown_preview',
        'resultado_markdown_html',
        'fecha_creacion',
        'fecha_actualizacion',
    )
    list_per_page = 25
    date_hierarchy = 'fecha_creacion'

    fieldsets = (
        ('Información Principal', {
            'fields': ('id', 'titulo', 'descripcion', 'tipo_servicio', 'proyecto')
        }),
        ('Medidas', {
            'fields': ('unidad_medida', 'cantidad')
        }),
        ('Clasificación IA', {
            'fields': ('clasificacion',),
            'classes': ('collapse',)
        }),
        ('Parámetros Técnicos (gestionados por IA)', {
            'fields': (
                'tabla_parametros_materiales',
                'tabla_parametros_ejecucion',
                'tabla_normas_aplicables',
                'tabla_criterios_calidad',
            ),
            'classes': ('collapse',)
        }),
        ('Actividades Adicionales (gestionadas por IA)', {
            'fields': ('tabla_actividades_adicionales',),
            'classes': ('collapse',)
        }),
        ('Resultado IA', {
            'fields': ('resumen', 'resultado_markdown_preview', 'resultado_markdown_html')
        }),
        ('Estado', {
            'fields': ('eliminado', 'paso'),
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )

    # ── Columnas de cada tabla ─────────────────────────────────────────────────

    _COLS_PARAMETROS = [
        ('parametro',         'Parámetro'),
        ('valor_recomendado', 'Valor'),
        ('unidad_medida',     'Unidad'),
        ('descripcion',       'Descripción'),
    ]
    _COLS_CRITERIOS = [
        ('parametro',         'Parámetro'),
        ('valor_recomendado', 'Valor'),
        ('descripcion',       'Descripción'),
    ]
    _COLS_NORMAS = [
        ('parametro',   'Norma'),
        ('descripcion', 'Descripción'),
    ]
    _COLS_ACTIVIDADES = [
        ('nombre',       'Actividad'),
        ('unidad_medida','Unidad'),
        ('descripcion',  'Descripción'),
    ]

    # ── Métodos de tabla ───────────────────────────────────────────────────────

    def tabla_parametros_materiales(self, obj):
        return _tabla_parametros(obj.parametros_materiales, self._COLS_PARAMETROS)
    tabla_parametros_materiales.short_description = 'Parámetros de Materiales'

    def tabla_parametros_ejecucion(self, obj):
        return _tabla_parametros(obj.parametros_ejecucion, self._COLS_PARAMETROS)
    tabla_parametros_ejecucion.short_description = 'Parámetros de Ejecución'

    def tabla_normas_aplicables(self, obj):
        return _tabla_parametros(obj.normas_aplicables, self._COLS_NORMAS)
    tabla_normas_aplicables.short_description = 'Normas Aplicables'

    def tabla_criterios_calidad(self, obj):
        return _tabla_parametros(obj.criterios_calidad, self._COLS_CRITERIOS)
    tabla_criterios_calidad.short_description = 'Criterios de Calidad'

    def tabla_actividades_adicionales(self, obj):
        return _tabla_parametros(obj.actividades_adicionales, self._COLS_ACTIVIDADES)
    tabla_actividades_adicionales.short_description = 'Actividades Adicionales'

    # ── Otros métodos ──────────────────────────────────────────────────────────

    def descripcion_corta(self, obj):
        if not obj.descripcion:
            return '-'
        palabras = obj.descripcion.split()[:12]
        texto = ' '.join(palabras)
        return texto + '...' if len(obj.descripcion.split()) > 12 else texto
    descripcion_corta.short_description = 'Descripción'

    def tiene_resultado(self, obj):
        if obj.resultado_markdown:
            return mark_safe('<span style="color:green;font-weight:bold;">✔</span>')
        return mark_safe('<span style="color:#ccc;">–</span>')
    tiene_resultado.short_description = 'Resultado'

    def resultado_markdown_preview(self, obj):
        if not obj.resultado_markdown:
            return '-'
        texto = obj.resultado_markdown
        texto = texto.replace('#', '').replace('*', '').replace('-', '')
        texto = ' '.join(texto.split())
        palabras = texto.split()[:20]
        preview = ' '.join(palabras)
        if len(texto.split()) > 20:
            preview += '...'
        return preview
    resultado_markdown_preview.short_description = 'Resultado (primeras 20 palabras)'

    def resultado_markdown_html(self, obj):
        if not obj.resultado_markdown:
            return '-'
        texto = obj.resultado_markdown
        texto = re.sub(r'^```markdown\s*\n?', '', texto, flags=re.MULTILINE)
        texto = re.sub(r'\n?\s*```\s*$', '', texto, flags=re.MULTILINE)
        texto = texto.strip()
        extensions = [
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.tables',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists',
        ]
        try:
            html = markdown.markdown(texto, output_format='html', extensions=extensions)
            return format_html('<div style="max-width:100%;overflow-x:auto;">{}</div>', mark_safe(html))
        except Exception:
            return format_html('<pre style="white-space:pre-wrap;">{}</pre>', texto)
    resultado_markdown_html.short_description = 'Resultado (HTML renderizado)'
