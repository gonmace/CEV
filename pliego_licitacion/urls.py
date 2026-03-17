from django.urls import path
from . import views

app_name = 'pliego_licitacion'

urlpatterns = [
    # Vista principal
    path('', views.pasos_view, name='pasos'),

    # Paso 1: Coherencia
    path('paso1/coherencia/', views.coherencia_view, name='coherencia'),

    # Pasos 1-1 a 1-4: clasificación (ejecutados en secuencia por el frontend)
    path('paso1-1/parametros-material/', views.parametros_material_view, name='parametros_material'),
    path('paso1-2/parametros-ejecucion/', views.parametros_ejecucion_view, name='parametros_ejecucion'),
    path('paso1-3/normas-aplicables/', views.normas_aplicables_view, name='normas_aplicables'),
    path('paso1-4/criterios-calidad/', views.criterios_calidad_view, name='criterios_calidad'),

    # Guardar sub-pasos individuales en sus campos JSON
    path('paso1-1/guardar/', views.guardar_parametros_materiales_view, name='guardar_parametros_materiales'),
    path('paso1-2/guardar/', views.guardar_parametros_ejecucion_view,  name='guardar_parametros_ejecucion'),
    path('paso1-3/guardar/', views.guardar_normas_aplicables_view,     name='guardar_normas_aplicables'),
    path('paso1-4/guardar/', views.guardar_criterios_calidad_view,     name='guardar_criterios_calidad'),

    # Paso 2: Confirmar parámetros (solo guarda en BD)
    path('paso2/confirmar/', views.confirmar_parametros_view, name='confirmar_parametros'),

    # Paso 3: Título (propuesta del webhook + guardar decisión)
    path('paso3/propuesta/', views.propuesta_titulo_view, name='propuesta_titulo'),
    path('paso3/guardar/', views.guardar_titulo_view, name='guardar_titulo'),

    # Paso 4: Actividades (sugerencias del webhook + guardar selección)
    path('paso4/adicionales/', views.adicionales_view, name='adicionales'),
    path('paso4/actividades/', views.actividades_view, name='actividades'),

    # Paso 5: Generar y mostrar resultado
    path('paso5/generar/', views.generar_resultado_view, name='generar_resultado'),
    path('paso5/resultado/', views.paso8_resultado_view, name='resultado'),
    path('paso5/guardar/', views.guardar_resultado_view, name='guardar_resultado'),

    # Utilidades
path('especificacion/<int:especificacion_tecnica_id>/eliminar/', views.eliminar_especificacion_tecnica_view, name='eliminar_especificacion_tecnica'),
    path('especificacion/<int:especificacion_tecnica_id>/datos/', views.get_especificacion_datos_view, name='get_especificacion_datos'),
]
