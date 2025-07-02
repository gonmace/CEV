from django.db import models
from django.contrib.auth import get_user_model

from .core_models import BaseModel, CoordinatesMixinModel

User = get_user_model()

class Site(BaseModel, CoordinatesMixinModel):
    pti_cell_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID_PTI")
    operator_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID_Operador")
    name = models.CharField(max_length=100, verbose_name="Nombre")
    lat = models.FloatField(null=True, blank=True, verbose_name="Latitud")
    lon = models.FloatField(null=True, blank=True, verbose_name="Longitud")
    alt = models.FloatField(null=True, blank=True, verbose_name="Altura")
    region = models.CharField(max_length=100, blank=True, null=True, verbose_name="Region/Provincia")
    comuna = models.CharField(max_length=100, blank=True, null=True, verbose_name="Comuna/Municipio")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Site'
        verbose_name_plural = 'Sites'

    def get_full_location(self):
        return f"{self.region}, {self.comuna}"

    @staticmethod
    def get_table():
        return 'site'

    @staticmethod
    def get_actives():
        return Site.objects.filter(is_deleted=False)
