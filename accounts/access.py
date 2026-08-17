"""Allow-list: quién puede entrar, con qué rol y como parte de qué empresa.

Hay dos vías de alta, y son las que definen los dos tipos de cuenta:

- **Empresa**: el correo pertenece al dominio de una `Empresa` activa. El usuario entra
  como miembro suyo, comparte su bolsa de créditos y ocupa una plaza de su cupo.
- **Personal**: el correo está habilitado uno a uno en `AllowedEmail`. No pertenece a
  ninguna empresa: sus créditos son suyos y no tiene equipo.
"""
from .models import AllowedEmail, Empresa, Role


def _split_domain(email):
    email = (email or '').strip().lower()
    if '@' not in email:
        return email, ''
    return email, email.rsplit('@', 1)[1]


def resolve_empresa(email):
    """La Empresa activa dueña del dominio del correo, o None si es una cuenta personal."""
    _, domain = _split_domain(email)
    if not domain:
        return None
    return Empresa.objects.filter(dominio=domain, is_active=True).first()


def is_email_allowed(email):
    """True si el correo puede darse de alta.

    Una excepción puntual (`AllowedEmail`) siempre vale: es el alta personal, y no está
    sujeta a cupo. El alta por dominio, en cambio, exige que la empresa tenga plazas
    libres — si está llena, el correo deja de estar permitido hasta que se amplíe el cupo
    o se libere una cuenta.
    """
    email, domain = _split_domain(email)
    if not domain:
        return False
    if AllowedEmail.objects.filter(email=email, is_active=True).exists():
        return True
    empresa = resolve_empresa(email)
    return bool(empresa and empresa.hay_cupo)


def resolve_default_role(email):
    """Rol predefinido para el correo: Usuario, salvo una excepción puntual por correo.

    Una empresa no tiene rol por defecto propio: todo miembro nuevo entra como Usuario,
    la promoción a Administrador es un paso manual y explícito (ver accounts.views.mi_equipo
    y access_admin) — así nadie hereda más poder del que alguien le dio a propósito.
    """
    email, _ = _split_domain(email)
    allowed_email = AllowedEmail.objects.filter(email=email, is_active=True).first()
    if allowed_email and allowed_email.default_role:
        return allowed_email.default_role
    return Role.USUARIO
