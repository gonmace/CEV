from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordResetForm, SetPasswordForm,
)
from django.template import loader

from core.mail import send_mail_async

from .models import AllowedEmail, EmailConfig, Empresa, Marca, Role

_INPUT = 'input input-bordered w-full'
_SELECT = 'select select-bordered w-full'
_CHECKBOX = 'checkbox checkbox-primary'
_FILE = 'file-input file-input-bordered w-full'


class BareClearableFileInput(forms.ClearableFileInput):
    """ClearableFileInput sin el "Currently: ... Clear <br> Change:" que Django renderiza
    por defecto — queda feo con DaisyUI. Solo dibuja el <input type=file>; el archivo
    actual y el checkbox de "Quitar" (mismo `-clear` que espera este widget) se arman a
    mano en el template, como un chip clickeable."""
    template_name = 'django/forms/widgets/file.html'


def role_choices_for(viewer):
    """Roles que `viewer` puede ver/asignar: ADMINISTRADOR solo lo asigna el superuser.

    Hoy la gestión de cuentas es superuser-only, así que en la práctica siempre devuelve
    todos los roles; se conserva como salvaguarda por si algún día se delega esa página."""
    if viewer is not None and viewer.is_superuser:
        return list(Role.choices)
    return [c for c in Role.choices if c[0] != Role.ADMINISTRADOR]


def _restrict_role_field(field, viewer):
    """Filtra ADMINISTRADOR de las choices de `field` (conserva la opción en blanco de
    los ModelForm) cuando el viewer no es superuser — vale también server-side: un POST
    con ese rol no pasa la validación del form."""
    allowed = {v for v, _ in role_choices_for(viewer)}
    field.choices = [c for c in field.choices if c[0] in allowed or not c[0]]


class RequestAccessForm(forms.Form):
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': _INPUT, 'autofocus': True, 'placeholder': 'tu.correo@empresa.com',
        }),
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class EmailAuthenticationForm(AuthenticationForm):
    """Login por correo + contraseña, con 'Recordarme'."""
    remember_me = forms.BooleanField(
        label='Recordarme', required=False, initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary checkbox-sm'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Correo electrónico'
        self.fields['username'].widget = forms.EmailInput(attrs={
            'class': _INPUT, 'autofocus': True, 'placeholder': 'tu.correo@empresa.com',
        })
        self.fields['password'].widget = forms.PasswordInput(attrs={
            'class': _INPUT, 'placeholder': '••••••••',
        })


class ActivationForm(SetPasswordForm):
    """Nombre, apellido y contraseña al activar la cuenta."""
    first_name = forms.CharField(label='Nombre', max_length=150, widget=forms.TextInput(
        attrs={'class': _INPUT, 'autofocus': True, 'placeholder': 'Nombre'}))
    last_name = forms.CharField(label='Apellido', max_length=150, widget=forms.TextInput(
        attrs={'class': _INPUT, 'placeholder': 'Apellido'}))
    field_order = ['first_name', 'last_name', 'new_password1', 'new_password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('new_password1', 'new_password2'):
            self.fields[name].widget = forms.PasswordInput(attrs={
                'class': _INPUT, 'placeholder': '••••••••',
            })

    def save(self, commit=True):
        self.user.first_name = self.cleaned_data['first_name'].strip()
        self.user.last_name = self.cleaned_data['last_name'].strip()
        return super().save(commit=commit)


class StyledSetPasswordForm(SetPasswordForm):
    """Solo contraseña, para el reseteo (a diferencia de ActivationForm, que además
    pide nombre/apellido para la activación inicial de cuenta)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('new_password1', 'new_password2'):
            self.fields[name].widget = forms.PasswordInput(attrs={
                'class': _INPUT, 'placeholder': '••••••••',
            })


class ProfileNameForm(forms.ModelForm):
    """Editar nombre y apellido del propio usuario."""
    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name')
        labels = {'first_name': 'Nombre', 'last_name': 'Apellido'}
        widgets = {
            'first_name': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Apellido'}),
        }


class AdminUserEditForm(forms.ModelForm):
    """El superuser (o un gestor con accounts.manage) edita nombre, apellido, rol y
    empresa de un usuario — para no-superusers el rol ADMINISTRADOR no se ofrece ni valida.

    La empresa se puede asignar a mano a CUALQUIER cuenta, sin importar si su correo es
    del dominio de esa empresa: el dominio solo decide la asignación automática al
    activarse (ver accounts.access.resolve_empresa); esto es la excepción manual —
    para gente contratada con un correo personal, consultores externos, etc."""
    role = forms.ChoiceField(label='Rol', choices=Role.choices,
                             widget=forms.Select(attrs={'class': _SELECT}))
    empresa = forms.ModelChoiceField(
        label='Empresa', queryset=Empresa.objects.filter(is_active=True), required=False,
        empty_label='— Cuenta personal —', widget=forms.Select(attrs={'class': _SELECT}),
        help_text='Se puede asignar aunque el correo de la cuenta no sea del dominio de la empresa.',
    )

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name')
        labels = {'first_name': 'Nombre', 'last_name': 'Apellido'}
        widgets = {
            'first_name': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Apellido'}),
        }

    def __init__(self, *args, viewer=None, **kwargs):
        super().__init__(*args, **kwargs)
        _restrict_role_field(self.fields['role'], viewer)
        if self.instance and self.instance.pk:
            prof = getattr(self.instance, 'profile', None)
            self.fields['role'].initial = prof.role if prof else Role.USUARIO
            self.fields['empresa'].initial = prof.empresa_id if prof else None


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget = forms.EmailInput(attrs={
            'class': _INPUT, 'autofocus': True, 'placeholder': 'tu.correo@empresa.com',
        })

    def send_mail(self, subject_template_name, email_template_name, context,
                  from_email, to_email, html_email_template_name=None):
        # Enruta el reset por core.mail: respeta la config SMTP de BD (EmailConfig)
        # y envía en background — from_email=None deja que resolve_from_email decida.
        subject = loader.render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)
        send_mail_async(subject, body, [to_email], from_email=None)


class InviteForm(forms.Form):
    email = forms.EmailField(
        label='Correo a invitar',
        widget=forms.EmailInput(attrs={'class': _INPUT, 'placeholder': 'persona@empresa.com'}),
    )
    role = forms.ChoiceField(
        label='Rol', choices=Role.choices, initial=Role.USUARIO,
        widget=forms.Select(attrs={'class': _SELECT}),
    )

    def __init__(self, *args, viewer=None, full_roles=False, **kwargs):
        super().__init__(*args, **kwargs)
        # full_roles: usado desde "Mi equipo" — ahí quien invita es un Administrador de
        # empresa (no superuser), pero SÍ puede elegir Administrador para su propio equipo
        # (ver accounts.permissions.is_company_admin). role_choices_for() asume que solo
        # el superuser ve ese rol, así que ese chequeo no aplica en ese contexto.
        if not full_roles:
            _restrict_role_field(self.fields['role'], viewer)

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ('nombre', 'dominio', 'max_usuarios', 'note')
        widgets = {
            'nombre': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nombre de la empresa'}),
            'dominio': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'empresa.com'}),
            'max_usuarios': forms.NumberInput(attrs={'class': _INPUT, 'min': 1, 'placeholder': 'Usuarios'}),
            'note': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nota (opcional)'}),
        }


class AllowedEmailForm(forms.ModelForm):
    class Meta:
        model = AllowedEmail
        fields = ('email', 'default_role', 'note')
        widgets = {
            'email': forms.EmailInput(attrs={'class': _INPUT, 'placeholder': 'persona@empresa.com'}),
            'default_role': forms.Select(attrs={'class': _SELECT}),
            'note': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nota (opcional)'}),
        }

    def __init__(self, *args, viewer=None, **kwargs):
        super().__init__(*args, **kwargs)
        _restrict_role_field(self.fields['default_role'], viewer)


class MarcaForm(forms.ModelForm):
    """Identidad visual de los documentos: logo, colores, datos y plantillas propias."""

    class Meta:
        model = Marca
        fields = (
            'nombre_mostrado', 'logo', 'color_primario', 'color_secundario',
            'identificacion_fiscal', 'direccion', 'telefono', 'sitio_web', 'pie_pagina',
            'plantilla_proyectos', 'plantilla_servicios',
        )
        widgets = {
            'nombre_mostrado': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Constructora Andes S.A.'}),
            'logo': BareClearableFileInput(attrs={'class': _FILE, 'accept': 'image/png,image/jpeg'}),
            # type=color: el navegador da el selector nativo, y el valor ya llega como #RRGGBB.
            'color_primario': forms.TextInput(attrs={'class': 'h-10 w-16 rounded cursor-pointer', 'type': 'color'}),
            'color_secundario': forms.TextInput(attrs={'class': 'h-10 w-16 rounded cursor-pointer', 'type': 'color'}),
            'identificacion_fiscal': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'NIT / RUT'}),
            'direccion': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Av. Siempre Viva 123'}),
            'telefono': forms.TextInput(attrs={'class': _INPUT, 'placeholder': '+591 700 00000'}),
            'sitio_web': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'www.empresa.com'}),
            'pie_pagina': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Documento confidencial'}),
            'plantilla_proyectos': BareClearableFileInput(attrs={'class': _FILE, 'accept': '.docx'}),
            'plantilla_servicios': BareClearableFileInput(attrs={'class': _FILE, 'accept': '.docx'}),
        }

    def _validar_docx(self, campo):
        archivo = self.cleaned_data.get(campo)
        # Solo se valida el archivo recién subido: si no cambió, viene el FieldFile de la BD.
        if archivo and hasattr(archivo, 'content_type'):
            if not archivo.name.lower().endswith('.docx'):
                raise forms.ValidationError('La plantilla debe ser un archivo .docx de Word.')
            if archivo.size > 10 * 1024 * 1024:
                raise forms.ValidationError('La plantilla no puede superar los 10 MB.')
        return archivo

    def clean_plantilla_proyectos(self):
        return self._validar_docx('plantilla_proyectos')

    def clean_plantilla_servicios(self):
        return self._validar_docx('plantilla_servicios')

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if logo and hasattr(logo, 'content_type') and logo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('El logo no puede superar los 5 MB.')
        return logo


class PlantillasForm(MarcaForm):
    """Solo las plantillas Word.

    Es la única parte de la marca que cada usuario puede definir por su cuenta: las del
    Administrador (en la marca de la empresa) son el default del equipo, y las que suba
    el usuario en su propia fila Marca las pisan (ver `marca.plantilla_de`).
    """

    class Meta(MarcaForm.Meta):
        fields = ('logo', 'plantilla_proyectos', 'plantilla_servicios')

    _CAMPO_POR_MODULO = {
        'pliegos.access': 'plantilla_proyectos',
        'servicios.access': 'plantilla_servicios',
    }

    def __init__(self, *args, modulos_activos=None, **kwargs):
        super().__init__(*args, **kwargs)
        if modulos_activos is not None:
            for modulo, campo in self._CAMPO_POR_MODULO.items():
                if modulo not in modulos_activos:
                    del self.fields[campo]


class EmailConfigForm(forms.ModelForm):
    """Editada solo por el superuser (accounts:email_config). La contraseña SMTP nunca
    se re-muestra: si se deja vacía al guardar, se conserva el valor existente."""
    password = forms.CharField(
        label='Contraseña', required=False,
        widget=forms.PasswordInput(attrs={
            'class': _INPUT, 'placeholder': 'Dejar en blanco para no cambiar', 'autocomplete': 'new-password',
        }, render_value=False),
        help_text='Se guarda pero nunca se vuelve a mostrar. Dejar vacía conserva la actual.',
    )

    class Meta:
        model = EmailConfig
        fields = ('enabled', 'host', 'port', 'use_tls', 'username', 'password', 'from_email')
        widgets = {
            'enabled': forms.CheckboxInput(attrs={'class': _CHECKBOX}),
            'host': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'smtp.dominio.com'}),
            'port': forms.NumberInput(attrs={'class': _INPUT, 'min': 1, 'max': 65535}),
            'use_tls': forms.CheckboxInput(attrs={'class': _CHECKBOX}),
            'username': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'usuario@dominio.com'}),
            'from_email': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'CEV <noreply@dominio>'}),
        }

    def clean_password(self):
        password = self.cleaned_data.get('password', '').strip()
        return password or (self.instance.password if self.instance else '')
