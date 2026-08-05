from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from manyumbu10.models import User


class Command(BaseCommand):
    help = "Seed local demo accounts for manual QA. Uses fictional data only."

    def add_arguments(self, parser):
        parser.add_argument("--allow-production", action="store_true", help="Explicitly allow running in production.")

    def handle(self, *args, **options):
        if getattr(settings, "MANYUMBU_ENV", "development") == "production" and not options["allow_production"]:
            raise CommandError("Refusing to seed demo data in production without --allow-production.")
        users = [
            ("+255799100001", "demo.alice@example.invalid", "demoalice", "Demo Alice"),
            ("+255799100002", "demo.bob@example.invalid", "demobob", "Demo Bob"),
            ("+255799100003", "demo.admin@example.invalid", "demoadmin", "Demo Admin"),
        ]
        created = 0
        for phone, email, username, full_name in users:
            user, was_created = User.objects.get_or_create(
                phone_number=phone,
                defaults={"email": email, "username": username, "full_name": full_name, "date_of_birth": "1995-01-01", "is_active": True, "is_email_verified": True},
            )
            if was_created:
                user.set_password("DemoPass123!")
                user.is_staff = username == "demoadmin"
                user.save()
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Demo seed complete. Created {created} users."))
