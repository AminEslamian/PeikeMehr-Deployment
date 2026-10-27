from rest_framework import serializers

from .models import Ticket

class TicketSerializer(serializers.ModelSerializer):
      class Meta:
            model = Ticket
            fields = [
                  "id",
                  "title",
                  "content",
                  "first_name",
                  "last_name",
                  "phone_number",
                  "answer",
                  "is_answered",
                  "created_at",
                  "updated_at",
            ]

            read_only_fields = [
                  "id",
                  "first_name",
                  "last_name",
                  "phone_number",
                  "answer",
                  "is_answered",
                  "created_at",
                  "updated_at",
            ]