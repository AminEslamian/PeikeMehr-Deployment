from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Teacher, OTPVerification, Grade

admin.site.register(Grade)
@admin.register(Teacher)
class TeacherAdmin(UserAdmin):
    model = Teacher

    list_display = (
        "phone_number",
        "first_name",
        "last_name",
        "national_id",
        "province",
        "city",
        "school",
        "position",
        "is_active",
        "is_staff",
        "gender"
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "province",
        "grade",
        "position",
        "gender"
    )

    search_fields = (
        "phone_number",
        "first_name",
        "last_name",
        "national_id",
        "school",
    )
    ordering = ("-created_at",)
    def display_grades(self, obj):
        return ", ".join(
            grade.name
            for grade in obj.grade.all()
        )

    display_grades.short_description = "پایه‌های تدریس"
    fieldsets = (
        (
            "اطلاعات حساب",
            {
                "fields": (
                    "phone_number",
                    "password",
                )
            },
        ),
        (
            "اطلاعات شخصی",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "national_id",
                )
            },
        ),
        (
            "اطلاعات محل",
            {
                "fields": (
                    "province",
                    "city",
                    "village",
                )
            },
        ),
        (
            "اطلاعات مدرسه",
            {
                "fields": (
                    "school",
                    "grade",
                    "position",
                )
            },
        ),
        (
            "دسترسی",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "تاریخ‌ها",
            {
                "fields": (
                    "last_login",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = (
        "last_login",
        "created_at",
        "updated_at",
    )

    add_fieldsets = (
        (
            "اطلاعات حساب",
            {
                "classes": ("wide",),
                "fields": (
                    "phone_number",
                    "password1",
                    "password2",
                ),
            },
        ),
        (
            "اطلاعات شخصی",
            {
                "classes": ("wide",),
                "fields": (
                    "first_name",
                    "last_name",
                    "national_id",
                ),
            },
        ),
        (
            "اطلاعات محل",
            {
                "classes": ("wide",),
                "fields": (
                    "province",
                    "city",
                    "village",
                ),
            },
        ),
        (
            "اطلاعات مدرسه",
            {
                "classes": ("wide",),
                "fields": (
                    "school",
                    "grade",
                    "position",
                ),
            },
        ),
        (
            "دسترسی",
            {
                "classes": ("wide",),
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):

    list_display = (
        "phone_number",
        "code",
        "created_at",
        "expires_at",
        "is_verified",
    )

    list_filter = (
        "is_verified",
        "created_at",
    )

    search_fields = (
        "phone_number",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
    )