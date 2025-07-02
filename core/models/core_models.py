from abc import ABCMeta, abstractmethod

from django.db import models
from django.utils import timezone


class BaseModelMeta(models.base.ModelBase, ABCMeta):
    pass


class BaseModel(models.Model, metaclass=BaseModelMeta):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    @staticmethod
    @abstractmethod
    def get_table():
        pass

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    @staticmethod
    @abstractmethod
    def get_actives():
        pass


class CoordinatesMixinModel(models.Model):
    # Coordenadas geográficas
    latitude = models.FloatField(verbose_name='Latitud', null=True, blank=True, help_text="Ejemplo: -33.4567")
    longitude = models.FloatField(verbose_name='Longitud', null=True, blank=True, help_text="Ejemplo: -70.6483")
    # Coordenadas GMS
    coordinates_gms = models.CharField(
        max_length=100,
        verbose_name='Coordenadas GMS',
        help_text='Formato: 33°27\'24.984"S, 70°38\'53.772"W',
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True

    @property
    def get_gms_coordinates_split(self):
        """Devuelve las coordenadas GMS como una lista de cadenas"""
        if self.coordinates_gms:
            array = self.coordinates_gms.split(", ")
            if len(array) == 2:
                lat_gms = array[0].strip()
                lon_gms = array[1].strip()
                return {
                    "latitude": lat_gms,
                    "longitude": lon_gms
                }
        return None

    def _decimal_to_gms(self, decimal, is_latitude=True):
        """Convierte una coordenada decimal a formato GMS"""
        direction = 'S' if decimal < 0 and is_latitude else 'N' if is_latitude else 'W' if decimal < 0 else 'E'
        decimal = abs(decimal)

        degrees = int(decimal)
        minutes_float = (decimal - degrees) * 60
        minutes = int(minutes_float)
        seconds = round((minutes_float - minutes) * 60, 3)

        return f"{degrees}°{minutes}'{seconds}\"{direction}"

    def update_gms(self):
        """Actualiza el campo GMS basado en latitud y longitud"""
        if self.latitude is not None and self.longitude is not None:
            lat_gms = self._decimal_to_gms(self.latitude, is_latitude=True)
            lon_gms = self._decimal_to_gms(self.longitude, is_latitude=False)
            self.coordinates_gms = f"{lat_gms}, {lon_gms}"

    def save(self, *args, **kwargs):
        self.update_gms()
        super().save(*args, **kwargs)
