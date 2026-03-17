from django.urls import path
from . import views

app_name = 'ubi_web'

urlpatterns = [
    path('crear/<int:proyecto_id>/', views.crear_ubicacion_view, name='crear_ubicacion'),
    path('editar/<int:ubicacion_id>/', views.editar_ubicacion_view, name='editar_ubicacion'),
    path('ubicacion/<int:ubicacion_id>/editar-contenido/', views.editar_contenido_ubicacion_view, name='editar_contenido_ubicacion'),
    path('ubicacion/eliminar/<int:ubicacion_id>/', views.eliminar_ubicacion_view, name='eliminar_ubicacion'),
    path('ubicacion/<int:ubicacion_id>/descargar-pdf/', views.descargar_pdf_ubicacion_view, name='descargar_pdf'),
    path('ubicacion/<int:ubicacion_id>/imagenes/', views.obtener_imagenes_ubicacion_view, name='obtener_imagenes_ubicacion'),
    path('ubicacion/<int:ubicacion_id>/subir-imagenes/', views.subir_imagenes_ubicacion_view, name='subir_imagenes_ubicacion'),
    path('ubicacion/imagen/<int:imagen_id>/eliminar/', views.eliminar_imagen_ubicacion_view, name='eliminar_imagen_ubicacion'),
    path('ubicacion/imagen/<int:imagen_id>/actualizar-descripcion/', views.actualizar_descripcion_imagen_ubicacion_view, name='actualizar_descripcion_imagen_ubicacion'),
]
