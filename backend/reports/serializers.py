from django.conf import settings
from django.db import transaction
from rest_framework import serializers

from config.uploads import (
    UnsupportedUpload,
    media_kind,
    validate_media_file,
)

from .models import Report, ReportImage, ReportVideo, Tag, Point

OTHER_TAG_REQUIRED_MESSAGE = (
    "اگر هیچ تگی انتخاب نشده باشد، باید موضوع «سایر» را وارد کنید."
)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class ReportImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportImage
        fields = ["id", "image", "created_at"]


class ReportVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportVideo
        fields = ["id", "video", "created_at"]


class ReportSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    other_tag = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )
    images = ReportImageSerializer(many=True, read_only=True)
    videos = ReportVideoSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "text",
            "tags",
            "other_tag",
            "images",
            "videos",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        # در به‌روزرسانی: اگر گزارش هیچ تگی ندارد، «سایر» نباید خالی شود
        if self.instance is not None and "other_tag" in attrs:
            other_tag = attrs["other_tag"].strip()
            attrs["other_tag"] = other_tag

            if not other_tag and not self.instance.tags.exists():
                raise serializers.ValidationError(
                    {"other_tag": OTHER_TAG_REQUIRED_MESSAGE}
                )

        return attrs


class TagIdsField(serializers.ManyRelatedField):
    """
    در multipart/form-data (مثلاً Swagger) فیلد خالی به شکل tags="" ارسال می‌شود.
    این فیلد مقدارهای خالی را نادیده می‌گیرد تا خطای
    "Incorrect type. Expected pk value" ایجاد نشود.
    """

    def get_value(self, dictionary):
        value = super().get_value(dictionary)
        if isinstance(value, list):
            value = [v for v in value if v not in ("", None)]
        return value


class ReportCreateSerializer(serializers.ModelSerializer):
    tags = TagIdsField(
        child_relation=serializers.PrimaryKeyRelatedField(
            queryset=Tag.objects.all()
        ),
        required=False,
    )
    other_tag = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )
    media = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Report
        fields = ["text", "tags", "other_tag", "media"]

    def validate_media(self, files):
        if len(files) > settings.MAX_UPLOAD_FILES:
            raise serializers.ValidationError(
                f"حداکثر تعداد فایل‌ها {settings.MAX_UPLOAD_FILES} عدد است."
            )

        for file in files:
            try:
                validate_media_file(file)
            except UnsupportedUpload as exc:
                raise serializers.ValidationError(
                    f"فایل {file.name}: {exc}"
                )

        return files

    def validate(self, attrs):
        tags = attrs.get("tags", [])
        other_tag = (attrs.get("other_tag") or "").strip()
        attrs["other_tag"] = other_tag

        # اگر تگی انتخاب نشد، «سایر» الزامی است
        if not tags and not other_tag:
            raise serializers.ValidationError(
                {"other_tag": OTHER_TAG_REQUIRED_MESSAGE}
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        media_files = validated_data.pop("media", [])
        user = self.context["request"].user
        report = Report.objects.create(teacher=user, **validated_data)

        if tags:
            report.tags.set(tags)

        for file in media_files:
            kind = media_kind(file)
            if kind == "image":
                ReportImage.objects.create(report=report, image=file)
            elif kind == "video":
                ReportVideo.objects.create(report=report, video=file)

        return report


class PointSerializer(serializers.ModelSerializer):
    class Meta:
        model = Point
        fields = [
            "id",
            "score",
            "reason",
            "created_at",
        ]


class PointsResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    points = PointSerializer(many=True)