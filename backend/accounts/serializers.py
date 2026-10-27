import re

from rest_framework import serializers
from .models import Grade, Teacher


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=16)

    def validate_phone_number(self, value):
        normalized = Teacher.objects.normalize_phone_number(str(value).strip())
        if not re.match(r"^09\d{9}$", normalized):
            raise serializers.ValidationError(
                "Phone number must contain exactly 11 digits and start with 09."
            )
        return normalized


class VerifyOTPSerializer(SendOTPSerializer):
    code = serializers.CharField(max_length=4)


class RegisterSendOTPSerializer(SendOTPSerializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    province = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=100)
    village = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )
    school = serializers.CharField(max_length=200)
    grade = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )
    position = serializers.ChoiceField(choices=Teacher.POSITION_CHOICES)
    gender = serializers.ChoiceField(
        choices=Teacher.GENDER_CHOICES,
        required=True,
    )
    national_id = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate_grade(self, value):
        values = list(dict.fromkeys(value))
        existing = set(
            Grade.objects.filter(value__in=values).values_list(
                "value", flat=True
            )
        )
        unknown = [item for item in values if item not in existing]
        if unknown:
            raise serializers.ValidationError(
                "Unknown grade value(s): " + ", ".join(unknown)
            )
        return values

    def validate_national_id(self, value):
        if value in (None, ""):
            return None
        value = str(value).strip()
        if not re.fullmatch(r"\d{10}", value):
            raise serializers.ValidationError(
                "National ID must contain exactly 10 digits."
            )
        return value


class RegisterVerifyOTPSerializer(RegisterSendOTPSerializer):
    code = serializers.CharField(max_length=4)


class TokenTeacherSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    phone_number = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField()


class OTPErrorSerializer(serializers.Serializer):
    error_code = serializers.CharField()


class LoginVerifyResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    teacher = TokenTeacherSerializer()
    redirect_url = serializers.CharField()


class RegisterVerifyResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    teacher = TokenTeacherSerializer()


# ----------------------------------------------------------------------
# Serializer
# ----------------------------------------------------------------------

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    شماره تماس فقط خواندنی است. پایه‌ها با مقدار Grade.value مبادله می‌شوند.
    """

    grade = serializers.SlugRelatedField(
        slug_field="value",
        queryset=Grade.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = Teacher
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone_number",
            "province",
            "city",
            "village",
            "school",
            "grade",
            "position",
            "gender",
            "national_id",
        ]
        read_only_fields = [
            "id",
            "phone_number",
        ]

