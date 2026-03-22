from django.conf import settings


def site_logo(request):
    return {
        'site_logo_url': getattr(settings, 'SITE_LOGO_URL', ''),
    }
