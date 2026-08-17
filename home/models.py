from django.db import models


class Configuracion(models.Model):
    nombre_empresa = models.CharField(
        max_length=200,
        default='Cliente',
        verbose_name='Nombre de empresa',
        help_text='Aparece en las especificaciones generadas por IA (ej: "EMBOL S.A.", "Coca-Cola Embonor"). Por defecto: Cliente.',
    )

    class Meta:
        verbose_name = 'Configuración'
        verbose_name_plural = 'Configuración'

    def __str__(self):
        return f'Configuración — {self.nombre_empresa}'

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton: siempre el mismo registro
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
