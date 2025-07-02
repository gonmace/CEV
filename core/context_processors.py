from django.conf import settings
from core.menu.menu_builder import MenuBuilder
from django.contrib.auth.models import AnonymousUser

def menu_context(request):
    return {
        'menu_items': MenuBuilder.get_menu(request.user, request.path, request)
    }