from django.db.models import Sum
from rest_framework import generics, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Point, Report, Tag
from .serializers import (
    PointSerializer,
    PointsResponseSerializer,
    ReportCreateSerializer,
    ReportSerializer,
    TagSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["Reports"], summary="لیست گزارش‌های کاربر"),
    retrieve=extend_schema(tags=["Reports"], summary="جزئیات گزارش"),
    create=extend_schema(
        tags=["Reports"],
        summary="ایجاد گزارش (multipart)",
        request={"multipart/form-data": ReportCreateSerializer},
        responses={201: ReportSerializer},
    ),
    update=extend_schema(tags=["Reports"], summary="به‌روزرسانی کامل گزارش"),
    partial_update=extend_schema(tags=["Reports"], summary="به‌روزرسانی جزئی گزارش"),
    destroy=extend_schema(tags=["Reports"], summary="حذف گزارش"),
)
class ReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Report.objects.none()
        return Report.objects.filter(
            teacher=self.request.user
        ).prefetch_related("tags", "images", "videos")

    def get_serializer_class(self):
        if self.action == "create":
            return ReportCreateSerializer
        return ReportSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        output_serializer = ReportSerializer(
            report,
            context=self.get_serializer_context(),
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Reports"], summary="لیست تگ‌ها")
class TagListView(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]


class MyPointsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PointsResponseSerializer

    @extend_schema(
        tags=["Reports"],
        summary="امتیازهای کاربر جاری",
        responses={200: PointsResponseSerializer},
    )
    def get(self, request):
        points = (
            Point.objects
            .filter(teacher=request.user)
            .order_by("-created_at")
        )

        total_points = points.aggregate(total=Sum("score"))["total"] or 0

        serializer = PointSerializer(
            points,
            many=True,
            context={"request": request}
        )

        return Response({
            "total": total_points,
            "points": serializer.data,
        })