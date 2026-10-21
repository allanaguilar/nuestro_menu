from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.households.models import Household
from apps.recipes.models import Recipe

DEV_RECIPES = [
    ("Lentejas estofadas", Recipe.Category.LEGUMBRES, 60),
    ("Pollo al horno", Recipe.Category.CARNE, 50),
    ("Merluza al vapor", Recipe.Category.PESCADO, 25),
    ("Espaguetis al pesto", Recipe.Category.PASTA, 20),
    ("Arroz con verduras", Recipe.Category.ARROZ, 35),
    ("Acelgas con patata", Recipe.Category.VERDURAS, 30),
    ("Tortilla de patatas", Recipe.Category.HUEVOS, 40),
    ("Garbanzos con espinacas", Recipe.Category.LEGUMBRES, 45),
    ("Quinoa con verduras", Recipe.Category.OTROS, 30),
    ("Salmón a la plancha", Recipe.Category.PESCADO, 20),
]


class Command(BaseCommand):
    help = "Crea recetas de ejemplo en el primer hogar. Solo desarrollo."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_dev solo está permitido con DEBUG=True.")
        household = Household.objects.order_by("created_at").first()
        if household is None:
            raise CommandError("Crea antes un hogar (registro en la web).")
        created = 0
        for name, category, minutes in DEV_RECIPES:
            _, was_created = Recipe.objects.get_or_create(
                household=household,
                normalized_name=name.casefold(),
                defaults={
                    "name": name,
                    "category": category,
                    "prep_time_minutes": minutes,
                    "notes": "Receta de desarrollo.",
                },
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Recetas nuevas: {created}"))
