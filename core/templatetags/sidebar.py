from django import template
from django.urls import resolve

register = template.Library()

@register.simple_tag(takes_context=True)
def is_menu_active(context, url_pattern):
    try:
        current_url = resolve(context['request'].path)
        base_url = current_url.url_name
        
        # Remove common suffixes to get base view name
        for suffix in ['_create', '_update', '_detail', '_list', '_edit']:
            base_url = base_url.replace(suffix, '')
            url_pattern = url_pattern.replace(suffix, '')
            
        return base_url == url_pattern
    except:
        return False