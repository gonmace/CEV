from django import template

register = template.Library()


@register.filter
def empresa_color(empresa):
    """Clase CSS de color único y consistente para una empresa, basado en su ID.

    Mismas clases avatar-c-N que ya usa proyectos.main_tags.user_avatar_color (ver
    theme/static_src/src/styles.css) — reutilizarlas evita duplicar la paleta.
    """
    if not empresa or not empresa.pk:
        return 'bg-base-200 text-base-content/40'
    return f'avatar-c-{empresa.pk % 10}'
