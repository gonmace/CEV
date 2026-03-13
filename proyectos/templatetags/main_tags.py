from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def sortable_header(
    label,
    field,
    current_sort_by,
    current_order,
    extra_classes="",
    sort_param="sort_by",
    order_param="order",
    extra_query="",
):
    """
    Renderiza un enlace de cabecera de tabla con icono de ordenamiento reutilizable.
    """
    is_active = current_sort_by == field
    next_order = "desc" if is_active and current_order == "asc" else "asc"

    icon = "fa-sort"
    icon_color_class = " text-primary-content/40"
    if is_active:
        icon = "fa-sort-up" if current_order == "asc" else "fa-sort-down"
        icon_color_class = " text-primary-content"

    base_classes = "flex items-center gap-2 hover:text-primary-content/70 transition-colors"
    classes = base_classes
    extra_classes = extra_classes.strip()
    if extra_classes:
        classes = f"{base_classes} {extra_classes}"

    icon_classes = f"fas {icon}{icon_color_class}"

    extra_query = extra_query.strip()
    query = f"{sort_param}={field}&{order_param}={next_order}"
    if extra_query:
        if not extra_query.startswith("&"):
            query = f"{query}&{extra_query}"
        else:
            query = f"{query}{extra_query}"

    return format_html(
        '<a href="?{query}" class="{classes}" onclick="event.stopPropagation();">'
        "<span>{label}</span>"
        '<i class="{icon_classes}"></i>'
        "</a>",
        query=query,
        classes=classes,
        label=label,
        icon_classes=icon_classes,
    )


@register.filter
def user_avatar_color(user):
    """
    Devuelve una clase CSS de color único y consistente para un usuario, basado en su ID.
    Las clases avatar-c-N están definidas en styles.css usando las variables del tema.
    """
    if not user or not user.pk:
        return "bg-base-200 text-base-content/40"
    return f"avatar-c-{user.pk % 10}"


@register.filter
def get_item(dictionary, key):
    """
    Filtro para acceder a un elemento de un diccionario por su clave.
    Uso: {{ dict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key, False)

