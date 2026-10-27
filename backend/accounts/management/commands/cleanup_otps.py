from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import OTPVerification


class Command(BaseCommand):
    help = "Delete old OTP rows (expired or already verified)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="Delete OTP rows older than this many days (default: 1).",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        deleted, _ = OTPVerification.objects.filter(
            created_at__lt=cutoff
        ).delete()
        self.stdout.write(f"Deleted {deleted} old OTP row(s).")
