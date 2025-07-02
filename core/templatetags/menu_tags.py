from django import template
from django.urls import resolve, reverse

register = template.Library()

@register.filter(name='is_menu_active')
def is_menu_active(request, menu_item):
    """Check if the current menu item is active.
    
    Args:
        context: The template context
        menu_item: The menu item to check
        
    Returns:
        bool: True if the menu item is active, False otherwise
    """
    current_url = request.path
    
    # Get the URL for the menu item
    try:
        menu_url = reverse(menu_item.url)
    except:
        return False
    
    # Check if the current URL exactly matches the menu URL

    if current_url == menu_url:
        return True
    
    # Check if the current URL starts with the menu URL (for nested routes)
    if current_url.startswith(menu_url) and menu_url != '/':
        return True
    
    # Check children if they exist
    if hasattr(menu_item, 'children') and menu_item.children:
        for child in menu_item.children:
            try:
                child_url = reverse(child.url)
                if current_url == child_url or (current_url.startswith(child_url) and child_url != '/'):
                    return True
            except:
                continue
    
    return False