from uuid import uuid4

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Verify the configured default storage by writing, reading and "
        "deleting a tiny object. Point this only at a test bucket until the "
        "real bucket has been approved."
    )

    def _download(self, url, expected):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(
                "Signed URL download failed: "
                f"{exc.__class__.__name__}"
            ) from exc

        if response.content != expected:
            raise CommandError(
                "Signed URL download returned unexpected data."
            )

    def _assert_private(self, url):
        unsigned_url = url.split("?", 1)[0]
        try:
            response = requests.get(unsigned_url, timeout=30)
        except requests.RequestException as exc:
            raise CommandError(
                "Unsigned URL check failed: "
                f"{exc.__class__.__name__}"
            ) from exc

        if response.status_code == 200:
            raise CommandError(
                "The uploaded object is publicly readable without a "
                "signature. Configure the bucket/object ACL as private."
            )

    def handle(self, *args, **options):
        name = f"healthchecks/storage-{uuid4().hex}.txt"
        payload = b"peykemehr-storage-check"
        saved_name = None
        signed_url_verified = False
        private_access_verified = False

        try:
            saved_name = default_storage.save(name, ContentFile(payload))

            if not default_storage.exists(saved_name):
                raise CommandError("Storage write succeeded but object is missing.")

            with default_storage.open(saved_name, "rb") as handle:
                if handle.read() != payload:
                    raise CommandError("Storage read returned unexpected data.")

            url = default_storage.url(saved_name)
            if url.startswith(("http://", "https://")):
                self._download(url, payload)
                signed_url_verified = True
                self._assert_private(url)
                private_access_verified = True
        except Exception as exc:
            if isinstance(exc, CommandError):
                raise
            raise CommandError(
                f"Storage check failed: {exc.__class__.__name__}"
            ) from exc
        finally:
            if saved_name:
                try:
                    default_storage.delete(saved_name)
                except Exception:
                    self.stderr.write(
                        "Warning: the storage test object could not be deleted."
                    )
                else:
                    if default_storage.exists(saved_name):
                        self.stderr.write(
                            "Warning: the storage test object still exists "
                            "after deletion."
                        )

        backend = default_storage.__class__.__name__
        checks = ["written", "read"]
        if signed_url_verified:
            checks.append("downloaded via signed URL")
        if private_access_verified:
            checks.append("unsigned access denied")
        checks.append("deleted")
        self.stdout.write(
            self.style.SUCCESS(
                f"Storage check OK using {backend} "
                f"({', '.join(checks)})."
            )
        )
