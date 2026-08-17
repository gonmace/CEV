from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone


class DemoTrial(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='demo_trial',
    )
    intentos_usados = models.PositiveSmallIntegerField(default=0)
    max_intentos = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name='Máx. intentos',
        help_text='Dejar vacío para usar el límite global (DEMO_MAX_TRIALS).',
    )
    fecha_primer_intento = models.DateTimeField(null=True, blank=True)
    fecha_ultimo_intento = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Demo Trial'
        verbose_name_plural = 'Demo Trials'

    def __str__(self):
        return f"{self.usuario.email} — {self.intentos_usados} intentos"

    def puede_intentar(self):
        limite = self.max_intentos if self.max_intentos is not None else getattr(settings, 'DEMO_MAX_TRIALS', 2)
        return self.intentos_usados < limite

    def registrar_intento(self):
        now = timezone.now()
        if not self.fecha_primer_intento:
            self.fecha_primer_intento = now
        self.fecha_ultimo_intento = now
        self.intentos_usados += 1
        self.save(update_fields=['intentos_usados', 'fecha_primer_intento', 'fecha_ultimo_intento'])
