from django.urls import path
from . import views

app_name = 'servicios'

urlpatterns = [
    path('', views.lista_servicios_view, name='lista_servicios'),
    path('nuevo/', views.crear_servicio_view, name='crear_servicio'),
    path('<int:servicio_id>/objetivo/', views.paso2_objetivo_view, name='paso2_objetivo'),
    path('<int:servicio_id>/objetivo/generar/', views.generar_objetivo_ajax, name='generar_objetivo_ajax'),
    path('<int:servicio_id>/alcance/', views.paso3_alcance_view, name='paso3_alcance'),
    path('<int:servicio_id>/alcance/clasificar/', views.clasificar_alcance_ajax, name='clasificar_alcance_ajax'),
    path('<int:servicio_id>/alcance/extraer-equipo/', views.extraer_equipo_ajax, name='extraer_equipo_ajax'),
    path('<int:servicio_id>/alcance/generar/', views.generar_alcance_ajax, name='generar_alcance_ajax'),
    path('<int:servicio_id>/', views.ver_servicio_view, name='ver_servicio'),
    path('<int:servicio_id>/editar/', views.editar_servicio_view, name='editar_servicio'),
    path('<int:servicio_id>/eliminar/', views.eliminar_servicio_view, name='eliminar_servicio'),
    path('<int:servicio_id>/imagenes/', views.obtener_imagenes_view, name='obtener_imagenes'),
    path('<int:servicio_id>/subir-imagenes/', views.subir_imagenes_view, name='subir_imagenes'),
    path('imagen/<int:imagen_id>/eliminar/', views.eliminar_imagen_view, name='eliminar_imagen'),
    path('imagen/<int:imagen_id>/descripcion/', views.actualizar_descripcion_imagen_view, name='actualizar_descripcion_imagen'),
    path('<int:servicio_id>/actividades/', views.obtener_actividades_view, name='obtener_actividades'),
    path('<int:servicio_id>/cantidad/', views.actualizar_cantidad_view, name='actualizar_cantidad'),
    path('<int:servicio_id>/actividad/<int:actividad_idx>/', views.actualizar_actividad_view, name='actualizar_actividad'),
    path('<int:servicio_id>/mostrar/', views.actualizar_mostrar_view, name='actualizar_mostrar'),
    path('extraer-pdf/', views.extraer_pdf_view, name='extraer_pdf'),
]
