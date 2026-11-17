import base64
import os
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Teacher
from reports.models import Report, ReportImage, ReportVideo, Tag

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def make_teacher(**kwargs):
    defaults = {
        "phone_number": "09123456789",
        "first_name": "Audit",
        "last_name": "Teacher",
        "province": "Qom",
        "city": "Qom",
        "school": "Audit School",
        "position": "teacher",
        "gender": "man",
        "national_id": "1234567890",
    }
    defaults.update(kwargs)
    return Teacher.objects.create(**defaults)


class ReportAPITests(APITestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._override = override_settings(MEDIA_ROOT=self._tmp)
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(shutil.rmtree, self._tmp, True)

        self.teacher = make_teacher()
        self.other = make_teacher(
            phone_number="09120000000",
            national_id="0000000001",
        )
        self.tag = Tag.objects.create(name="Classroom")
        self.url = "/api/reports/"

    def _image(self, name="photo.png", content_type="image/png"):
        return SimpleUploadedFile(name, PNG_BYTES, content_type=content_type)

    def test_unauthenticated_list_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tag_list_is_public(self):
        response = self.client.get("/api/reports/tags/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_only_sees_own_reports(self):
        own = Report.objects.create(teacher=self.teacher, text="own")
        Report.objects.create(teacher=self.other, text="other")
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [own.id])

    def test_user_cannot_retrieve_other_report(self):
        other = Report.objects.create(teacher=self.other, text="other")
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f"{self.url}{other.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_delete_other_report(self):
        other = Report.objects.create(teacher=self.other, text="other")
        self.client.force_authenticate(user=self.teacher)

        response = self.client.delete(f"{self.url}{other.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Report.objects.filter(pk=other.id).exists())

    def test_create_requires_text(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self.url,
            {"tags": [self.tag.id]},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_requires_tag_or_other_tag(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self.url,
            {"text": "A class activity"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_tag_succeeds(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self.url,
            {"text": "A class activity", "tags": [self.tag.id]},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Report.objects.filter(teacher=self.teacher).count(), 1)

    def test_create_rejects_unsupported_content_type(self):
        self.client.force_authenticate(user=self.teacher)
        pdf = SimpleUploadedFile("doc.pdf", b"%PDF-1.4", content_type="application/pdf")
        response = self.client.post(
            self.url,
            {"text": "A class activity", "tags": [self.tag.id], "media": [pdf]},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_more_than_twenty_files(self):
        self.client.force_authenticate(user=self.teacher)
        files = [self._image(f"photo-{i}.png") for i in range(21)]
        response = self.client.post(
            self.url,
            {"text": "A class activity", "tags": [self.tag.id], "media": files},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_accepts_image_and_video(self):
        self.client.force_authenticate(user=self.teacher)
        video = SimpleUploadedFile("clip.mp4", b"\x00\x00\x00\x18ftypmp42", content_type="video/mp4")
        response = self.client.post(
            self.url,
            {
                "text": "A class activity",
                "tags": [self.tag.id],
                "media": [self._image(), video],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ReportImage.objects.count(), 1)
        self.assertEqual(ReportVideo.objects.count(), 1)

    def test_create_rejects_spoofed_html_disguised_as_image(self):
        self.client.force_authenticate(user=self.teacher)
        spoof = SimpleUploadedFile(
            "payload.html",
            b"<script>alert(document.cookie)</script>",
            content_type="image/png",
        )
        response = self.client.post(
            self.url,
            {"text": "A class activity", "tags": [self.tag.id], "media": [spoof]},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_valid_image_with_unsafe_extension(self):
        self.client.force_authenticate(user=self.teacher)
        disguised = SimpleUploadedFile(
            "payload.html",
            PNG_BYTES,
            content_type="image/png",
        )
        response = self.client.post(
            self.url,
            {"text": "A class activity", "tags": [self.tag.id], "media": [disguised]},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(MAX_UPLOAD_SIZE=10)
    def test_create_rejects_file_over_configured_size(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self.url,
            {"text": "A class activity", "tags": [self.tag.id], "media": [self._image()]},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_removes_media_file(self):
        self.client.force_authenticate(user=self.teacher)
        create = self.client.post(
            self.url,
            {"text": "A class activity", "tags": [self.tag.id], "media": [self._image()]},
            format="multipart",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)

        image = ReportImage.objects.get()
        stored_path = image.image.path

        delete = self.client.delete(f"{self.url}{create.data['id']}/")
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(os.path.exists(stored_path))

    def test_list_is_not_paginated(self):
        Report.objects.create(teacher=self.teacher, text="own")
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


class StorageIntegrationTests(APITestCase):
    """Local test double used when real S3 credentials are unavailable."""

    @override_settings(
        STORAGES={
            "default": {
                "BACKEND": "django.core.files.storage.InMemoryStorage",
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        }
    )
    def test_default_storage_can_write_read_and_delete(self):
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage

        name = default_storage.save(
            "reports/images/storage-check.png",
            ContentFile(PNG_BYTES),
        )
        self.assertTrue(default_storage.exists(name))
        with default_storage.open(name, "rb") as handle:
            self.assertEqual(handle.read(), PNG_BYTES)

        default_storage.delete(name)
        self.assertFalse(default_storage.exists(name))
