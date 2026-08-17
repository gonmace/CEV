"""Empresas (evolución de AllowedDomain) + sistema de créditos por módulo.

`AllowedDomain` se RENOMBRA a `Empresa`: es el mismo concepto (un dominio habilitado),
ahora con nombre, cupo de usuarios y bolsa de créditos. Se usa RenameModel/RenameField a
propósito, NO Delete+Create: eso borraría los dominios ya habilitados en producción (es el
mismo error que cometió pliego_licitacion/0017, que sí perdió datos).
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def poblar_nombres_y_vincular(apps, schema_editor):
    """Rellena el nombre de las empresas ya existentes y vincula a sus usuarios.

    Hasta ahora la pertenencia usuario→dominio era implícita (el sufijo del email); a
    partir de aquí es una FK explícita, así que hay que materializarla para las cuentas
    que ya existen.
    """
    Empresa = apps.get_model('accounts', 'Empresa')
    Profile = apps.get_model('accounts', 'Profile')

    for empresa in Empresa.objects.all():
        if not empresa.nombre:
            empresa.nombre = empresa.dominio
            empresa.save(update_fields=['nombre'])

        # Vincula las cuentas cuyo correo pertenece a este dominio.
        for profile in Profile.objects.filter(
            user__email__iendswith=f'@{empresa.dominio}', empresa__isnull=True,
        ):
            profile.empresa = empresa
            profile.save(update_fields=['empresa'])


def desvincular(apps, schema_editor):
    Profile = apps.get_model('accounts', 'Profile')
    Profile.objects.update(empresa=None)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0004_module_capabilities'),
    ]

    operations = [
        # ── AllowedDomain → Empresa (rename real, sin pérdida de datos) ──────────
        migrations.RenameModel(old_name='AllowedDomain', new_name='Empresa'),
        migrations.RenameField(model_name='empresa', old_name='domain', new_name='dominio'),
        migrations.AlterModelOptions(
            name='empresa',
            options={
                'ordering': ['dominio'],
                'verbose_name': 'Empresa',
                'verbose_name_plural': 'Empresas',
            },
        ),
        migrations.AddField(
            model_name='empresa',
            name='nombre',
            # default='' y lo rellena la data migration de abajo con el dominio.
            field=models.CharField(default='', max_length=120, verbose_name='Nombre'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='empresa',
            name='max_usuarios',
            field=models.PositiveIntegerField(
                default=5,
                help_text='Cuántas cuentas activas puede tener la empresa.',
                verbose_name='Máximo de usuarios',
            ),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='dominio',
            field=models.CharField(
                help_text='Dominio de correo de la empresa, ej. "empresa.com".',
                max_length=255, unique=True, verbose_name='Dominio',
            ),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='default_role',
            field=models.CharField(
                blank=True,
                choices=[('USUARIO', 'Usuario'), ('ADMINISTRADOR', 'Administrador')],
                help_text='Rol asignado a los usuarios de esta empresa (Usuario si se deja vacío).',
                max_length=20, verbose_name='Rol por defecto',
            ),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Activa'),
        ),

        # ── Pertenencia del usuario a una empresa ────────────────────────────────
        migrations.AddField(
            model_name='profile',
            name='empresa',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Vacío = cuenta personal (créditos propios, sin equipo).',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='miembros', to='accounts.empresa', verbose_name='Empresa',
            ),
        ),

        # ── Créditos ────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='BolsaCreditos',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modulo', models.CharField(max_length=50, verbose_name='Módulo')),
                ('creditos', models.PositiveIntegerField(default=0, verbose_name='Créditos')),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('empresa', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name='bolsas', to='accounts.empresa')),
                ('usuario', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name='bolsas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Bolsa de créditos',
                'verbose_name_plural': 'Bolsas de créditos',
            },
        ),
        migrations.CreateModel(
            name='TopeUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modulo', models.CharField(max_length=50, verbose_name='Módulo')),
                ('tope', models.PositiveIntegerField(
                    help_text='Máximo de créditos que esta persona puede consumir del total.',
                    verbose_name='Tope')),
                ('usuario', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='topes',
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Tope de usuario',
                'verbose_name_plural': 'Topes de usuario',
                'unique_together': {('usuario', 'modulo')},
            },
        ),
        migrations.CreateModel(
            name='ConsumoCredito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modulo', models.CharField(max_length=50, verbose_name='Módulo')),
                ('cantidad', models.PositiveSmallIntegerField(default=1, verbose_name='Cantidad')),
                ('referencia', models.CharField(
                    blank=True, help_text='Qué se generó, ej. "EspecificacionTecnica#42".',
                    max_length=200, verbose_name='Referencia')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('empresa', models.ForeignKey(
                    blank=True, null=True,
                    help_text='Vacío = el consumo salió de la bolsa personal del usuario.',
                    on_delete=django.db.models.deletion.SET_NULL, related_name='consumos',
                    to='accounts.empresa')),
                ('usuario', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='consumos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Consumo de créditos',
                'verbose_name_plural': 'Consumos de créditos',
                'ordering': ['-fecha'],
            },
        ),
        migrations.AddIndex(
            model_name='consumocredito',
            index=models.Index(fields=['usuario', 'modulo'], name='accounts_co_usuario_f2e897_idx'),
        ),
        migrations.AddConstraint(
            model_name='bolsacreditos',
            constraint=models.UniqueConstraint(
                fields=('empresa', 'modulo'), name='bolsa_unica_por_empresa_modulo'),
        ),
        migrations.AddConstraint(
            model_name='bolsacreditos',
            constraint=models.UniqueConstraint(
                fields=('usuario', 'modulo'), name='bolsa_unica_por_usuario_modulo'),
        ),
        migrations.AddConstraint(
            model_name='bolsacreditos',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(('empresa__isnull', False), ('usuario__isnull', True))
                    | models.Q(('empresa__isnull', True), ('usuario__isnull', False))
                ),
                name='bolsa_de_empresa_o_de_usuario',
            ),
        ),

        migrations.RunPython(poblar_nombres_y_vincular, desvincular),
    ]
