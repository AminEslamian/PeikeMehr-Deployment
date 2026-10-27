
from rest_framework import viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Blog
from .serializers import BlogSerializer


@extend_schema_view(
    list=extend_schema(tags=["Blogs"], summary="لیست بلاگ‌ها"),
    retrieve=extend_schema(tags=["Blogs"], summary="جزئیات بلاگ"),
    create=extend_schema(
        tags=["Blogs"],
        summary="ایجاد بلاگ (ادمین)",
        request={"multipart/form-data": BlogSerializer},
    ),
    update=extend_schema(
        tags=["Blogs"],
        summary="به‌روزرسانی کامل بلاگ (ادمین)",
        request={"multipart/form-data": BlogSerializer},
    ),
    partial_update=extend_schema(
        tags=["Blogs"],
        summary="به‌روزرسانی جزئی بلاگ (ادمین)",
        request={"multipart/form-data": BlogSerializer},
    ),
    destroy=extend_schema(tags=["Blogs"], summary="حذف بلاگ (ادمین)"),
)
class BlogViewSet(viewsets.ModelViewSet):

    queryset = Blog.objects.all().order_by("-created_at")
    serializer_class = BlogSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):

        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
        ]:
            return [IsAdminUser()]

        return [IsAuthenticated()]