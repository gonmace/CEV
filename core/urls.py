from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from django.contrib.auth.views import LoginView, LogoutView
from home.sitemaps import StaticViewSitemap

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
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/login/', LoginView.as_view(template_name='login.html')),
    path('logout/', LogoutView.as_view(next_page='/login/'), name='logout'),
    path('', include('home.urls')),
    path('proyectos/', include('proyectos.urls')),
    path('servicios/', include('servicios.urls')),
    path('pliego/', include('pliego_licitacion.urls')),
    path('ubicaciones/', include('ubi_web.urls')),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path('__reload__/', include('django_browser_reload.urls'))]
