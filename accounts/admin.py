from django.contrib import admin

from .models import (
    AllowedEmail, BolsaCreditos, ConsumoCredito, Empresa, Profile, RolePermission,
    TopeUsuario,
)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dominio', 'usuarios_activos', 'max_usuarios', 'is_active', 'created')
    list_filter = ('is_active',)
    search_fields = ('nombre', 'dominio')


@admin.register(AllowedEmail)
class AllowedEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'default_role', 'is_active', 'created')
    list_filter = ('is_active', 'default_role')
    search_fields = ('email',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'empresa', 'created')
    list_filter = ('role', 'empresa')
    search_fields = ('user__email', 'user__username')
    autocomplete_fields = ('user',)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'capability', 'enabled')
    list_filter = ('role', 'enabled')
    search_fields = ('capability',)


@admin.register(BolsaCreditos)
class BolsaCreditosAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'empresa', 'usuario', 'modulo', 'creditos', 'actualizado')
    list_filter = ('modulo',)
    search_fields = ('empresa__nombre', 'usuario__email')


@admin.register(TopeUsuario)
class TopeUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'modulo', 'tope')
    list_filter = ('modulo',)
    search_fields = ('usuario__email',)


@admin.register(ConsumoCredito)
class ConsumoCreditoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'usuario', 'empresa', 'modulo', 'cantidad', 'referencia')
    list_filter = ('modulo', 'empresa')
    search_fields = ('usuario__email', 'referencia')
    readonly_fields = ('fecha',)
