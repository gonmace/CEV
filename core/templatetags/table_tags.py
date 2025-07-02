from django import template

register = template.Library()


@register.filter(name='get_attr')
def get_attr(obj, attr):
    """
    Gets an attribute of an object dynamically from a string name
    """
    if '.' in attr:
        attrs = attr.split('.')
        value = obj
        for a in attrs:
            if hasattr(value, a):
                value = getattr(value, a)
                if callable(value):
                    value = value()
            else:
                return ''
        return value

    value = getattr(obj, attr, '')

    if callable(value):
        return value()
    return value or ""


@register.filter(name='format_url')
def format_url(url_pattern, item):
    """
    Format URL pattern with item attributes
    Example: "company:edit {item.id}" -> "company:edit 1"
    """
    try:
        # Extract the variable part from the URL pattern
        if '{' in url_pattern:
            pattern, var = url_pattern.split(' ')
            var = var.strip('{}')
            # Get the attribute value using the variable path
            attr_path = var.split('.')
            value = item
            for attr in attr_path[1:]:  # Skip 'item' part
                value = getattr(value, attr)
            return f"{pattern} {value}"
        return url_pattern
    except Exception:
        return '#'


@register.filter(name='concat')
def concat(value, arg):
    print("value", value, type(value))
    print("arg", arg, type(arg))
    return f"{value}{arg}"


@register.filter(name='reverse_lazy')
def reverse_lazy(value):
    """
    Reverse a URL pattern name
    """
    try:
        from django.urls import reverse
        return reverse(value)
    except Exception:
        return '#'