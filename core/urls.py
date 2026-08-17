from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.contrib.sitemaps.views import sitemap
from home.sitemaps import StaticViewSitemap
import home.views as home_views

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt',
        content_type='text/plain',
        extra_context={'ADMIN_URL': settings.ADMIN_URL},
    )),
    path('acceso/', include('accounts.urls')),
    # Compatibilidad: /login/ viejo (bookmarks, name='login' en templates) → login nuevo.
    path('login/', RedirectView.as_view(pattern_name='accounts:login', query_string=True), name='login'),
    path('logout/', home_views.logout_view, name='logout'),
    path('accounts/', include('allauth.urls')),
    path('', include('home.urls')),
    path('proyectos/', include('proyectos.urls')),
    path('servicios/', include('servicios.urls')),
    path('pliego/', include('pliego_licitacion.urls')),
    path('ubicaciones/', include('ubi_web.urls')),
    path('demo/', include('demo.urls')),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path('__reload__/', include('django_browser_reload.urls'))]
