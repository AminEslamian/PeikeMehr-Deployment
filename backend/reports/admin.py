from django.contrib import admin

from .models import Report, Tag, ReportImage, ReportVideo


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "created_at",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "name",
    )


class ReportImageInline(admin.TabularInline):
    model = ReportImage
    extra = 1


class ReportVideoInline(admin.TabularInline):
    model = ReportVideo
    extra = 1


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "teacher",
        "short_text",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "created_at",
        "updated_at",
        "tags",
    )

    search_fields = (
        "text",
        "teacher__phone_number",
        "teacher__first_name",
        "teacher__last_name",
    )

    filter_horizontal = (
        "tags",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        ReportImageInline,
        ReportVideoInline,
    ]

    @admin.display(description="متن گزارش")
    def short_text(self, obj):
        if len(obj.text) > 60:
            return obj.text[:60] + "..."
        return obj.text


@admin.register(ReportImage)
class ReportImageAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "report",
        "created_at",
    )

    search_fields = (
        "report__text",
        "report__teacher__phone_number",
        "report__teacher__first_name",
        "report__teacher__last_name",
    )

    list_filter = (
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )


@admin.register(ReportVideo)
class ReportVideoAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "report",
        "created_at",
    )

    search_fields = (
        "report__text",
        "report__teacher__phone_number",
        "report__teacher__first_name",
        "report__teacher__last_name",
    )

    list_filter = (
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )
