import json
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.html import format_html, mark_safe
from .models import Servicio, ServicioImagen, CatalogoServicios


@admin.register(CatalogoServicios)
class CatalogoServiciosAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'num_categorias', 'fecha_actualizacion')
    list_editable = ('activo',)
    readonly_fields = ('fecha_actualizacion',)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<int:pk>/editar-catalogo/',
                self.admin_site.admin_view(self.editar_catalogo_view),
                name='servicios_catalogo_editar',
            ),
        ]
        return custom + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Redirige el botón "Cambiar" del admin al editor visual."""
        return HttpResponseRedirect(
            reverse('admin:servicios_catalogo_editar', args=[object_id])
        )

    def editar_catalogo_view(self, request, pk):
        catalogo = get_object_or_404(CatalogoServicios, pk=pk)

        if request.method == 'POST':
            raw = request.POST.get('datos_json', '[]')
            try:
                datos = json.loads(raw)
                catalogo.datos = datos
                catalogo.save(update_fields=['datos'])
                messages.success(request, 'Catálogo guardado correctamente.')
                return HttpResponseRedirect(
                    reverse('admin:servicios_catalogo_editar', args=[pk])
                )
            except json.JSONDecodeError:
                messages.error(request, 'Error al procesar el JSON. No se guardó.')

        context = {
            **self.admin_site.each_context(request),
            'catalogo': catalogo,
            'datos_json': json.dumps(catalogo.datos or [], ensure_ascii=False),
            'title': f'Editar catálogo: {catalogo.nombre}',
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/servicios/editar_catalogo.html', context)

    def num_categorias(self, obj):
        datos = obj.datos or []
        total_subs = sum(len(c.get('subcategorias', [])) for c in datos)
        return f"{len(datos)} cat. / {total_subs} subcat."
    num_categorias.short_description = "Tamaño"


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'subcategoria_codigo', 'categoria_nombre', 'creado_por', 'fecha_creacion', 'activo', 'publico')
    list_filter = ('activo', 'publico', 'fecha_creacion', 'categoria_nombre')
    search_fields = ('titulo', 'subcategoria_codigo', 'subcategoria_nombre', 'categoria_nombre')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'equipos_display', 'actividades_adicionales_display')
    fieldsets = (
        (None, {'fields': ('titulo', 'categoria_nombre', 'subcategoria_codigo', 'subcategoria_nombre', 'creado_por', 'activo', 'publico', 'mostrar', 'orden')}),
        ('Contenido', {'fields': ('descripcion', 'objetivo', 'alcance_generado', 'alcance_editado', 'contenido', 'unidad_medida', 'cantidad')}),
        ('Equipos', {'fields': ('equipos_display',)}),
        ('Actividades adicionales', {'fields': ('actividades_adicionales_display',), 'classes': ('collapse',)}),
        ('Fechas', {'fields': ('fecha_creacion', 'fecha_actualizacion')}),
    )

    def _render_json_lista(self, items, campos):
        """Renderiza una lista de dicts como tabla HTML para el admin."""
        if not items:
            return mark_safe('<span style="color:#999">—</span>')
        filas = []
        for i, item in enumerate(items, 1):
            celdas = ''.join(
                f'<tr><td style="padding:3px 8px;color:#666;font-size:0.8em;vertical-align:top;white-space:nowrap">'
                f'<strong>{label}</strong></td>'
                f'<td style="padding:3px 8px;font-size:0.85em">{item.get(key) or "—"}</td></tr>'
                for key, label in campos if key != '__espec__'
            )
            # Especificaciones (sub-objeto)
            espec = item.get('especificaciones', {})
            if espec:
                caract = ', '.join(espec.get('caracteristicas') or []) or '—'
                func   = ', '.join(espec.get('funcionamiento') or []) or '—'
                celdas += (
                    f'<tr><td style="padding:3px 8px;color:#666;font-size:0.8em;vertical-align:top"><strong>Características</strong></td>'
                    f'<td style="padding:3px 8px;font-size:0.85em">{caract}</td></tr>'
                    f'<tr><td style="padding:3px 8px;color:#666;font-size:0.8em;vertical-align:top"><strong>Funcionamiento</strong></td>'
                    f'<td style="padding:3px 8px;font-size:0.85em">{func}</td></tr>'
                )
            relevante = item.get('relevante', True)
            color = '#e8f5e9' if relevante else '#fff8e1'
            border = '#a5d6a7' if relevante else '#ffe082'
            filas.append(
                f'<div style="margin-bottom:8px;border:1px solid {border};border-radius:6px;'
                f'background:{color};overflow:hidden">'
                f'<div style="padding:4px 8px;background:{border};font-weight:bold;font-size:0.85em">'
                f'{i}. {item.get("nombre") or "Equipo sin nombre"}</div>'
                f'<table style="width:100%;border-collapse:collapse">{celdas}</table></div>'
            )
        return mark_safe(''.join(filas))

    def equipos_display(self, obj):
        campos = [
            ('tipo_equipo', 'Tipo'),
            ('marca', 'Marca'),
            ('modelo', 'Modelo'),
            ('capacidad', 'Capacidad'),
            ('descripcion', 'Descripción'),
            ('__espec__', ''),
        ]
        return self._render_json_lista(obj.equipos or [], campos)
    equipos_display.short_description = 'Equipos'

    def actividades_adicionales_display(self, obj):
        items = obj.actividades_adicionales or []
        if not items:
            return mark_safe('<span style="color:#999">—</span>')
        filas = []
        for i, act in enumerate(items, 1):
            nombre = act.get('nombre') or act.get('actividad') or f'Actividad {i}'
            resto = ''.join(
                f'<tr><td style="padding:2px 8px;color:#666;font-size:0.8em;white-space:nowrap"><strong>{k}</strong></td>'
                f'<td style="padding:2px 8px;font-size:0.85em">{v}</td></tr>'
                for k, v in act.items() if k not in ('nombre', 'actividad') and v
            )
            filas.append(
                f'<div style="margin-bottom:6px;border:1px solid #b3c6e0;border-radius:5px;background:#f0f4ff;overflow:hidden">'
                f'<div style="padding:3px 8px;background:#b3c6e0;font-weight:bold;font-size:0.85em">{i}. {nombre}</div>'
                f'<table style="width:100%;border-collapse:collapse">{resto}</table></div>'
            )
        return mark_safe(''.join(filas))
    actividades_adicionales_display.short_description = 'Actividades adicionales'


@admin.register(ServicioImagen)
class ServicioImagenAdmin(admin.ModelAdmin):
    list_display = ('servicio', 'descripcion', 'fecha_subida')
    list_filter = ('fecha_subida',)
    search_fields = ('servicio__titulo', 'descripcion')
