import re
from django.core.management.base import BaseCommand
from pliego_licitacion.models import EspecificacionTecnica


class Command(BaseCommand):
    help = 'Cambia ## por ### y ### por #### en todos los campos contenido de EspecificacionTecnica'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra cuántos registros serían afectados sin modificar nada',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        actualizados = 0

        especificaciones = EspecificacionTecnica.objects.exclude(resultado_markdown__isnull=True).exclude(resultado_markdown='')

        for esp in especificaciones:
            contenido_original = esp.resultado_markdown

            # Primero ### → #### (para no convertir ## dos veces)
            nuevo = re.sub(r'^###(?!#)', '####', contenido_original, flags=re.MULTILINE)
            # Luego ## → ###
            nuevo = re.sub(r'^##(?!#)', '###', nuevo, flags=re.MULTILINE)

            if nuevo != contenido_original:
                actualizados += 1
                if not dry_run:
                    esp.resultado_markdown = nuevo
                    esp.save(update_fields=['resultado_markdown'])
                else:
                    self.stdout.write(f'  [dry-run] id={esp.id} sería actualizado')

        if dry_run:
            self.stdout.write(self.style.WARNING(f'Dry-run: {actualizados} registros serían actualizados.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'{actualizados} registros actualizados correctamente.'))
