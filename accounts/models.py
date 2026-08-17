from django.conf import settings
from django.db import models


class Role(models.TextChoices):
    USUARIO = 'USUARIO', 'Usuario'
    ADMINISTRADOR = 'ADMINISTRADOR', 'Administrador'


class Empresa(models.Model):
    """Cuenta de empresa: se identifica por su dominio de correo.

    Quien se dé de alta con un correo de este dominio entra como miembro de la empresa
    (ver accounts.access.resolve_empresa), consume de su bolsa de créditos compartida y
    cuenta para su cupo de usuarios. Una cuenta SIN empresa es una cuenta personal.
    """
    nombre = models.CharField('Nombre', max_length=120)
    dominio = models.CharField(
        'Dominio', max_length=255, unique=True,
        help_text='Dominio de correo de la empresa, ej. "empresa.com".',
    )
    max_usuarios = models.PositiveIntegerField(
        'Máximo de usuarios', default=5,
        help_text='Cuántas cuentas activas puede tener la empresa.',
    )
    is_active = models.BooleanField('Activa', default=True)
    note = models.CharField('Nota', max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['dominio']
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def save(self, *args, **kwargs):
        self.dominio = self.dominio.strip().lower().lstrip('@')
        if not self.nombre:
            self.nombre = self.dominio
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre or self.dominio

    @property
    def usuarios_activos(self):
        return self.miembros.filter(user__is_active=True).count()

    @property
    def hay_cupo(self):
        return self.usuarios_activos < self.max_usuarios


class AllowedEmail(models.Model):
    """Correo puntual habilitado (excepción a un dominio no listado)."""
    email = models.EmailField('Correo', unique=True)
    is_active = models.BooleanField('Activo', default=True)
    default_role = models.CharField(
        'Rol por defecto', max_length=20, choices=Role.choices, blank=True,
    )
    note = models.CharField('Nota', max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['email']
        verbose_name = 'Correo permitido'
        verbose_name_plural = 'Correos permitidos'

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class Profile(models.Model):
    """Datos extra del usuario: su rol y la empresa a la que pertenece (si pertenece a alguna)."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile',
    )
    role = models.CharField('Rol', max_length=20, choices=Role.choices, default=Role.USUARIO)
    empresa = models.ForeignKey(
        Empresa, null=True, blank=True, on_delete=models.SET_NULL, related_name='miembros',
        verbose_name='Empresa',
        help_text='Vacío = cuenta personal (créditos propios, sin equipo).',
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'

    def __str__(self):
        return f'{self.user} ({self.get_role_display()})'

    @property
    def es_personal(self):
        return self.empresa_id is None


class EmailConfig(models.Model):
    """Config de correo saliente SMTP (fila única, pk=1), editable por el superuser.

    Si `enabled` y hay `host`, pisa la configuración del .env. Con `enabled=False`
    se sigue usando el backend del settings.
    """
    enabled = models.BooleanField(
        'Usar esta configuración SMTP', default=False,
        help_text='Apagado: se usa la configuración de correo del servidor (.env).',
    )
    host = models.CharField('Servidor SMTP', max_length=255, blank=True)
    port = models.PositiveIntegerField('Puerto', default=587)
    use_tls = models.BooleanField('Usar TLS', default=True)
    username = models.CharField('Usuario', max_length=255, blank=True)
    password = models.CharField('Contraseña', max_length=500, blank=True)
    from_email = models.CharField(
        'Remitente', max_length=255, blank=True,
        help_text='Ej. CEV <noreply@dominio>. Vacío = el del servidor.',
    )
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración de correo'
        verbose_name_plural = 'Configuración de correo'

    def __str__(self):
        return f'Correo ({"SMTP propio" if self.enabled else "settings"})'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class RolePermission(models.Model):
    """Matriz rol × capacidad, editable por el superuser en el tablero de toggles."""
    role = models.CharField(max_length=20, choices=Role.choices)
    capability = models.CharField(max_length=50)
    enabled = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'capability')
        ordering = ['role', 'capability']
        verbose_name = 'Permiso de rol'
        verbose_name_plural = 'Permisos de roles'

    def __str__(self):
        return f'{self.role}:{self.capability}={self.enabled}'


class UserPermission(models.Model):
    """Override puntual de una capacidad para UN usuario — pisa el default de
    RolePermission cuando existe una fila para (user, capability). Aplica a cualquier
    rol y sobrevive a los cambios de rol. Solo el superuser lo edita, desde la ficha del
    usuario (accounts:user_edit)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='permission_overrides',
    )
    capability = models.CharField(max_length=50)
    enabled = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'capability')
        ordering = ['user_id', 'capability']
        verbose_name = 'Permiso de usuario'
        verbose_name_plural = 'Permisos de usuario'

    def __str__(self):
        return f'{self.user_id}:{self.capability}={self.enabled}'


# ── Créditos ────────────────────────────────────────────────────────────────────
# Un crédito = un entregable generado con IA (un pliego, un servicio). Los pasos
# intermedios del flujo no cuestan. El saldo se lleva por módulo, porque un cliente
# puede contratar Proyectos y no Servicios. La clave de `modulo` son las de
# accounts.permissions.MODULE_KEYS ('pliegos.access' / 'servicios.access').

class BolsaCreditos(models.Model):
    """Saldo de créditos de un módulo. Es de una empresa (bolsa compartida por todo su
    equipo) o de un usuario suelto (cuenta personal), nunca de ambos."""
    empresa = models.ForeignKey(
        Empresa, null=True, blank=True, on_delete=models.CASCADE, related_name='bolsas',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.CASCADE, related_name='bolsas',
    )
    modulo = models.CharField('Módulo', max_length=50)
    creditos = models.PositiveIntegerField('Créditos', default=0)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bolsa de créditos'
        verbose_name_plural = 'Bolsas de créditos'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'modulo'], name='bolsa_unica_por_empresa_modulo',
            ),
            models.UniqueConstraint(
                fields=['usuario', 'modulo'], name='bolsa_unica_por_usuario_modulo',
            ),
            # Una bolsa cuelga de una empresa O de un usuario, nunca de los dos ni de
            # ninguno: si no, no se sabría a quién se le descuenta.
            models.CheckConstraint(
                condition=(
                    models.Q(empresa__isnull=False, usuario__isnull=True)
                    | models.Q(empresa__isnull=True, usuario__isnull=False)
                ),
                name='bolsa_de_empresa_o_de_usuario',
            ),
        ]

    def __str__(self):
        dueno = self.empresa or self.usuario
        return f'{dueno} · {self.modulo}: {self.creditos}'


class TopeUsuario(models.Model):
    """Tope de gasto de un miembro sobre la bolsa compartida de su empresa.

    Sin fila = sin tope (puede gastar toda la bolsa). Solo tiene sentido para usuarios
    con empresa; en una cuenta personal el tope es su propio saldo."""
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='topes',
    )
    modulo = models.CharField('Módulo', max_length=50)
    tope = models.PositiveIntegerField(
        'Tope', help_text='Máximo de créditos que esta persona puede consumir del total.',
    )

    class Meta:
        unique_together = ('usuario', 'modulo')
        verbose_name = 'Tope de usuario'
        verbose_name_plural = 'Topes de usuario'

    def __str__(self):
        return f'{self.usuario_id}:{self.modulo} ≤ {self.tope}'


class ConsumoCredito(models.Model):
    """Un consumo registrado. Sirve de historial para el superuser y es la base con la
    que se calcula el tope individual (cuánto lleva gastado cada miembro)."""
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        related_name='consumos',
    )
    empresa = models.ForeignKey(
        Empresa, null=True, blank=True, on_delete=models.SET_NULL, related_name='consumos',
        help_text='Vacío = el consumo salió de la bolsa personal del usuario.',
    )
    modulo = models.CharField('Módulo', max_length=50)
    cantidad = models.PositiveSmallIntegerField('Cantidad', default=1)
    referencia = models.CharField(
        'Referencia', max_length=200, blank=True,
        help_text='Qué se generó, ej. "EspecificacionTecnica#42".',
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Consumo de créditos'
        verbose_name_plural = 'Consumos de créditos'
        indexes = [
            models.Index(fields=['usuario', 'modulo']),
        ]

    def __str__(self):
        return f'{self.usuario_id} · {self.modulo} · -{self.cantidad}'


# ── Marca (identidad visual de los documentos) ──────────────────────────────────

def marca_upload_path(instance, filename):
    dueno = f'empresa_{instance.empresa_id}' if instance.empresa_id else f'usuario_{instance.usuario_id}'
    return f'marca/{dueno}/{filename}'


class Marca(models.Model):
    """Identidad visual con la que salen los documentos generados: logo, colores, datos de
    contacto y, si hace falta, una plantilla Word propia.

    Es de una empresa (la comparte todo su equipo) o de una cuenta personal, nunca de ambos
    — mismo patrón que BolsaCreditos. Sin fila, se usan las plantillas por defecto del
    sistema, así que esto es opcional: nadie queda bloqueado por no configurarlo.
    """
    empresa = models.OneToOneField(
        Empresa, null=True, blank=True, on_delete=models.CASCADE, related_name='marca',
    )
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.CASCADE, related_name='marca',
    )

    # ── Identidad ───────────────────────────────────────────────────────────
    nombre_mostrado = models.CharField(
        'Nombre en los documentos', max_length=120, blank=True,
        help_text='Cómo aparece el nombre en portada y pie. Vacío = el nombre de la cuenta.',
    )
    logo = models.ImageField(
        'Logo', upload_to=marca_upload_path, null=True, blank=True,
        help_text='Reemplaza el logo de la plantilla. PNG o JPG, fondo transparente si es posible.',
    )
    color_primario = models.CharField(
        'Color principal', max_length=7, default='#1f2937',
        help_text='Títulos y encabezados de tabla en el documento. Formato #RRGGBB.',
    )
    color_secundario = models.CharField(
        'Color secundario', max_length=7, default='#6b7280',
        help_text='Subtítulos y detalles. Formato #RRGGBB.',
    )

    # ── Datos que se imprimen en los documentos ─────────────────────────────
    identificacion_fiscal = models.CharField('NIT / RUT', max_length=40, blank=True)
    direccion = models.CharField('Dirección', max_length=200, blank=True)
    telefono = models.CharField('Teléfono', max_length=50, blank=True)
    sitio_web = models.CharField('Sitio web', max_length=120, blank=True)
    pie_pagina = models.CharField(
        'Pie de página', max_length=200, blank=True,
        help_text='Texto al pie de cada página del documento.',
    )

    # ── Plantillas propias (opcionales) ─────────────────────────────────────
    # Si no se sube ninguna, se usa la del sistema. Deben conservar los placeholders
    # (<<PROYECTO>>, <<SOLICITANTE>>, …) o esos campos saldrán vacíos.
    plantilla_proyectos = models.FileField(
        'Plantilla Word — Proyectos', upload_to=marca_upload_path, null=True, blank=True,
        help_text='.docx propio para las especificaciones de proyectos.',
    )
    plantilla_servicios = models.FileField(
        'Plantilla Word — Servicios', upload_to=marca_upload_path, null=True, blank=True,
        help_text='.docx propio para las especificaciones de servicios.',
    )

    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(empresa__isnull=False, usuario__isnull=True)
                    | models.Q(empresa__isnull=True, usuario__isnull=False)
                ),
                name='marca_de_empresa_o_de_usuario',
            ),
        ]

    _CAMPOS_ARCHIVO = ('logo', 'plantilla_proyectos', 'plantilla_servicios')

    def __str__(self):
        return f'Marca de {self.empresa or self.usuario}'

    def save(self, *args, **kwargs):
        """Borra del storage el archivo que un campo reemplaza o pierde al guardar, para
        que no queden huérfanos (Django, por defecto, nunca borra el archivo viejo solo
        porque el campo apunte a otro nuevo o quede vacío)."""
        if self.pk:
            anterior = Marca.objects.filter(pk=self.pk).first()
            if anterior:
                for campo in self._CAMPOS_ARCHIVO:
                    archivo_anterior = getattr(anterior, campo)
                    archivo_nuevo = getattr(self, campo)
                    if archivo_anterior and archivo_anterior.name != archivo_nuevo.name:
                        archivo_anterior.delete(save=False)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        archivos = [getattr(self, campo) for campo in self._CAMPOS_ARCHIVO]
        resultado = super().delete(*args, **kwargs)
        for archivo in archivos:
            if archivo:
                archivo.delete(save=False)
        return resultado

    @property
    def titular(self):
        return self.empresa or self.usuario

    def nombre(self):
        """El nombre a imprimir: el configurado, o el de la empresa/persona."""
        if self.nombre_mostrado:
            return self.nombre_mostrado
        if self.empresa:
            return self.empresa.nombre
        return self.usuario.get_full_name() or self.usuario.username
