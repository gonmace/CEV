from django import template

register = template.Library()


@register.filter
def endswith(value, arg):
    """
    Verifica si una cadena termina con un valor específico
    Uso: {{ value|endswith:'pdf' }}
    """
    if value is None:
        return False
    return str(value).lower().endswith(str(arg).lower())


@register.filter
def startswith(value, arg):
    """
    Verifica si una cadena comienza con un valor específico
    Uso: {{ value|startswith:'http' }}
    """
    if value is None:
        return False
    return str(value).lower().startswith(str(arg).lower())