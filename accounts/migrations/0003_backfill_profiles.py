from django.db import migrations


def backfill_profiles(apps, schema_editor):
    """Crea un Profile con rol Usuario para todo User existente sin profile —
    cubre los usuarios previos de CEV y los ya creados vía Google (allauth).
    Los usuarios Google futuros sin Profile quedan cubiertos por el fallback de
    accounts.permissions.get_user_role."""
    User = apps.get_model('auth', 'User')
    Profile = apps.get_model('accounts', 'Profile')
    for user in User.objects.filter(profile__isnull=True):
        Profile.objects.create(user=user, role='USUARIO')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_seed_permissions'),
    ]

    operations = [
        migrations.RunPython(backfill_profiles, migrations.RunPython.noop),
    ]
