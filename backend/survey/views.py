from rest_framework import serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from .models import Survey
from .serializers import (
    SubmissionCreateSerializer,
    SurveyDetailSerializer,
    SurveyListSerializer,
)


class SurveySubmitResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


@extend_schema_view(
    list=extend_schema(tags=["Surveys"], summary="لیست نظرسنجی‌های فعال"),
    retrieve=extend_schema(tags=["Surveys"], summary="جزئیات نظرسنجی و پاسخ قبلی"),
)
class SurveyViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = (
        Survey.objects.filter(is_active=True)
        .prefetch_related("questions__options")
        .order_by("-created_at")
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SurveyDetailSerializer
        return SurveyListSerializer

    @extend_schema(
        tags=["Surveys"],
        summary="ثبت یا به‌روزرسانی پاسخ نظرسنجی",
        request=SubmissionCreateSerializer,
        responses={
            201: OpenApiResponse(response=SurveySubmitResponseSerializer),
        },
    )
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        survey = self.get_object()

        serializer = SubmissionCreateSerializer(
            data=request.data,
            context={"request": request, "survey": survey},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "پاسخ‌های شما با موفقیت ثبت شد."},
            status=status.HTTP_201_CREATED,
        )