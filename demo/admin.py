from django.contrib import admin
from .models import DemoTrial


@admin.register(DemoTrial)
class DemoTrialAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'intentos_usados', 'max_intentos', 'puede_intentar', 'fecha_primer_intento', 'fecha_ultimo_intento')
    list_editable = ('intentos_usados', 'max_intentos')
    list_filter = ('intentos_usados',)
    search_fields = ('usuario__email', 'usuario__username')
    readonly_fields = ('fecha_primer_intento', 'fecha_ultimo_intento')
    ordering = ('-fecha_ultimo_intento',)

    @admin.display(boolean=True, description='¿Puede intentar?')
    def puede_intentar(self, obj):
        return obj.puede_intentar()
