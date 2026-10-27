from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status,viewsets
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import Teacher, OTPVerification, Grade
import secrets
from django.shortcuts import get_object_or_404
from .serializers import (
    SendOTPSerializer,
    VerifyOTPSerializer,
    RegisterSendOTPSerializer,
    RegisterVerifyOTPSerializer,
    ProfileUpdateSerializer,
    MessageSerializer,
    OTPErrorSerializer,
    LoginVerifyResponseSerializer,
    RegisterVerifyResponseSerializer,
)
from .services import send_sms, _generate_tokens
from .sms import SMSDeliveryError
from .throttles import OTPSendThrottle, OTPVerifyThrottle



def normalize_phone_number(phone_number: str) -> str:
    if phone_number.startswith("+98"):
        return "0" + phone_number[3:]
    return phone_number


def check_rate_limit(phone_number: str) -> bool:
    return OTPVerification.objects.filter(
        phone_number=phone_number,
        created_at__gte=timezone.now()
        - timedelta(seconds=settings.OTP_RESEND_SECONDS),
    ).exists()


def verify_otp_code(phone_number: str, code: str):
    otp = OTPVerification.objects.filter(
        phone_number=phone_number, is_verified=False
    ).order_by("-created_at").first()
    
    if not otp:
        return None, "No active OTP found."

    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        otp.delete()
        return None, "Too many attempts. Please request a new OTP."
    
    if otp.is_expired:
        return None, "OTP has expired."
    
    if otp.code != code:
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        return None, "Invalid OTP code."
    
    return otp, None


def _create_and_send_otp(phone_number: str):
    """
    Create an OTP and deliver it. Returns an error Response on failure, or
    None on success. A failed delivery must never be reported as success.
    """
    code = str(secrets.randbelow(9000) + 1000)
    otp = OTPVerification.create_otp(phone_number, code=code)

    try:
        send_sms(phone_number, code)
    except SMSDeliveryError:
        otp.delete()
        return Response(
            {
                "detail": (
                    "The verification code could not be sent. "
                    "Please try again later."
                )
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return None


class SendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPSendThrottle]
    serializer_class = SendOTPSerializer

    @extend_schema(
        tags=["Auth"],
        summary="ارسال OTP ورود",
        request=SendOTPSerializer,
        responses={
            200: OpenApiResponse(response=MessageSerializer, description="OTP ارسال شد"),
            404: OpenApiResponse(response=MessageSerializer, description="شماره ثبت نشده"),
            429: OpenApiResponse(response=MessageSerializer, description="محدودیت نرخ"),
        },
    )
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = normalize_phone_number(serializer.validated_data["phone_number"])

        if not Teacher.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"detail": "Phone number doesn't exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if check_rate_limit(phone_number):
            return Response(
                {"detail": "Please wait before requesting another OTP."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        delivery_error = _create_and_send_otp(phone_number)
        if delivery_error:
            return delivery_error

        return Response({"detail": "OTP sent successfully."}, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]
    serializer_class = VerifyOTPSerializer

    @extend_schema(
        tags=["Auth"],
        summary="تأیید OTP ورود و دریافت JWT",
        request=VerifyOTPSerializer,
        responses={
            200: OpenApiResponse(response=LoginVerifyResponseSerializer),
            400: OpenApiResponse(response=OTPErrorSerializer),
        },
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = normalize_phone_number(
            serializer.validated_data["phone_number"]
        )
        code = serializer.validated_data["code"]

        otp, error = verify_otp_code(phone_number, code)

        if error:
            return Response(
                {
                    "error_code": error,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        teacher = get_object_or_404(Teacher, phone_number=phone_number)

        otp.delete()

        tokens = _generate_tokens(teacher)

        if teacher.is_superuser:
            redirect_url = "/admin-panel/"
        else:
            redirect_url = "/main/"

        return Response(
            {
                **tokens,
                "redirect_url": redirect_url,
            },
            status=status.HTTP_200_OK,
        )   


class RegisterSendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPSendThrottle]
    serializer_class = RegisterSendOTPSerializer

    @extend_schema(
        tags=["Auth"],
        summary="ارسال OTP ثبت‌نام",
        request=RegisterSendOTPSerializer,
        responses={
            200: OpenApiResponse(response=MessageSerializer),
            400: OpenApiResponse(response=MessageSerializer),
            429: OpenApiResponse(response=MessageSerializer),
        },
    )
    def post(self, request):
        serializer = RegisterSendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]
        national_id = (serializer.validated_data.get("national_id") or "").strip()
        if Teacher.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"detail": "This phone number is already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if national_id and Teacher.objects.filter(national_id=national_id).exists():
            return Response(
                {"detail": "This national ID is already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if check_rate_limit(phone_number):
            return Response(
                {"detail": "Please wait before requesting another OTP."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        delivery_error = _create_and_send_otp(phone_number)
        if delivery_error:
            return delivery_error

        return Response({"detail": "OTP sent successfully."}, status=status.HTTP_200_OK)


class RegisterVerifyOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]
    serializer_class = RegisterVerifyOTPSerializer

    @extend_schema(
        tags=["Auth"],
        summary="تأیید OTP ثبت‌نام، ساخت کاربر و دریافت JWT",
        request=RegisterVerifyOTPSerializer,
        responses={
            201: OpenApiResponse(response=RegisterVerifyResponseSerializer),
            400: OpenApiResponse(response=MessageSerializer),
        },
    )
    def post(self, request):
        serializer = RegisterVerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        phone_number = normalize_phone_number(data["phone_number"])
        code = data["code"]
        national_id = (data.get("national_id") or "").strip() or None

        otp, error = verify_otp_code(phone_number, code)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        if Teacher.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"detail": "This phone number is already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if national_id and Teacher.objects.filter(national_id=national_id).exists():
            return Response(
                {"detail": "This national ID is already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            teacher = Teacher.objects.create(
                phone_number=phone_number,
                first_name=data["first_name"],
                last_name=data["last_name"],
                province=data["province"],
                city=data["city"],
                village=data.get("village", ""),
                school=data["school"],
                position=data["position"],
                national_id=national_id,
                gender = data["gender"],
                is_active=True,
            )
            grades = Grade.objects.filter(value__in=data["grade"])
            teacher.grade.set(grades)

            otp.is_verified = True
            otp.save(update_fields=["is_verified"])

        response_data = _generate_tokens(teacher)
        response_data["teacher"] = {
            "id": teacher.id,
            "phone_number": teacher.phone_number,
            "first_name": teacher.first_name,
            "last_name": teacher.last_name,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

# ----------------------------------------------------------------------
# ViewSet
# ----------------------------------------------------------------------

class ProfileViewSet(viewsets.ModelViewSet):
    """
    کاربر فقط می‌تواند پروفایل خودش را ببیند و ویرایش کند.
    ایجاد، حذف و لیست کردن کاربران غیرفعال است.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProfileUpdateSerializer
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_queryset(self):
        return Teacher.objects.filter(pk=self.request.user.pk)

    def get_object(self):
        obj = self.request.user
        self.check_object_permissions(self.request, obj)
        return obj


