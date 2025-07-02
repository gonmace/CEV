from django.urls import path

from core.views.sitios import SitiosView

app_name = "sitios"

urlpatterns = [
    path("", SitiosView.as_view(), name="sitios_list"),
]
