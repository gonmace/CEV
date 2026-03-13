from django.urls import path
from . import views

app_name = 'pliego_licitacion'

urlpatterns = [
    path('', views.pasos_view, name='pasos'),
    # path('parametros-paso2/', views.parametros_paso2_view, name='parametros_paso2'),  # Eliminada: paso 2 ahora es modal
    path('guardar-paso1/', views.guardar_paso1_view, name='guardar_paso1'),
    path('enviar-especificacion/', views.enviar_especificacion_view, name='enviar_especificacion'),
    path('enviar-parametros/', views.enviar_parametros_seleccionados_view, name='enviar_parametros'),
    path('enviar-titulo-ajustado/', views.enviar_titulo_ajustado_view, name='enviar_titulo_ajustado'),
    path('enviar-actividades/', views.enviar_actividades_view, name='enviar_actividades'),
    path('paso5-resultado/', views.paso5_resultado_view, name='paso5_resultado'),
    path('guardar-resultado/', views.guardar_resultado_view, name='guardar_resultado'),
    path('especificacion-tecnica/<int:especificacion_tecnica_id>/actualizar-cantidad/', views.actualizar_cantidad_especificacion_tecnica_view, name='actualizar_cantidad_especificacion_tecnica'),
    path('actividad-adicional/<int:actividad_id>/actualizar-cantidad/', views.actualizar_cantidad_actividad_view, name='actualizar_cantidad_actividad'),
]






