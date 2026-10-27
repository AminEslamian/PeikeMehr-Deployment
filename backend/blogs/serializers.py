# blogs/serializers.py

from rest_framework import serializers

from config.uploads import UnsupportedUpload, validate_media_file

from .models import Blog


class BlogSerializer(serializers.ModelSerializer):

    class Meta:
        model = Blog
        fields = [
            "id",
            "title",
            "content",
            "media",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_media(self, value):
        try:
            validate_media_file(value)
        except UnsupportedUpload as exc:
            raise serializers.ValidationError(str(exc))

        return value