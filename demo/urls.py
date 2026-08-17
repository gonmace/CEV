from django.urls import path
from . import views

app_name = 'demo'

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('iniciar/', views.iniciar_demo_view, name='iniciar'),
    path('flujo/', views.flujo_paso1_view, name='flujo_paso1'),
    path('flujo/parametros/<int:especificacion_id>/', views.flujo_paso2_view, name='flujo_paso2'),
    path('flujo/resultado/<int:especificacion_id>/', views.flujo_resultado_view, name='flujo_resultado'),
    path('resultado/<int:especificacion_id>/', views.resultado_demo_view, name='resultado'),
]
