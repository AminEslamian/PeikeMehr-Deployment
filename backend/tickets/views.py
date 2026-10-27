from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Ticket
from .serializers import (
TicketSerializer,
)

@extend_schema_view(
    list=extend_schema(tags=["Tickets"], summary="لیست تیکت‌های کاربر"),
    retrieve=extend_schema(tags=["Tickets"], summary="جزئیات تیکت"),
    create=extend_schema(tags=["Tickets"], summary="ایجاد تیکت"),
    update=extend_schema(tags=["Tickets"], summary="به‌روزرسانی کامل تیکت"),
    partial_update=extend_schema(tags=["Tickets"], summary="به‌روزرسانی جزئی تیکت"),
    destroy=extend_schema(tags=["Tickets"], summary="حذف تیکت"),
)
class TicketViewSet(viewsets.ModelViewSet):
      serializer_class = TicketSerializer
      permission_classes = [IsAuthenticated]

      def get_queryset(self):
            if getattr(self, "swagger_fake_view", False):
                  return Ticket.objects.none()
            return Ticket.objects.filter(
            phone_number=self.request.user.phone_number
            ).order_by("-created_at")

      def perform_create(self, serializer):
            serializer.save(
                  first_name=self.request.user.first_name,
                  last_name=self.request.user.last_name,
                  phone_number=self.request.user.phone_number,
            )