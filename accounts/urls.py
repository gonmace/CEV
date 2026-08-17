from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import StyledPasswordResetForm, StyledSetPasswordForm

app_name = 'accounts'

urlpatterns = [
    # Onboarding / login
    path('solicitar/', views.request_access, name='request_access'),
    path('activar/<uidb64>/<token>/', views.activate, name='activate'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('perfil/', views.profile, name='profile'),
    path('logout/', auth_views.LogoutView.as_view(next_page='accounts:login'), name='logout'),

    # Password reset (vistas built-in con templates propios)
    path('password/reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/emails/password_reset.txt',
        subject_template_name='accounts/emails/password_reset_subject.txt',
        form_class=StyledPasswordResetForm,
        success_url=reverse_lazy('accounts:password_reset_done'),
    ), name='password_reset'),
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        form_class=StyledSetPasswordForm,
        success_url=reverse_lazy('accounts:password_reset_complete'),
    ), name='password_reset_confirm'),
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),

    # Administración
    path('admin/', views.access_admin, name='access_admin'),
    path('equipo/', views.mi_equipo, name='mi_equipo'),
    path('cuenta/<int:pk>/', views.user_edit, name='user_edit'),
    path('roles/', views.roles_board, name='roles_board'),
    path('configuracion/', views.configuracion, name='configuracion'),
    path('correo/', views.email_config, name='email_config'),
    path('impersonar/', views.impersonate, name='impersonate'),
]
