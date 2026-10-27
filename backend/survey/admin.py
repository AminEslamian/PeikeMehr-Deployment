from django.contrib import admin
from nested_admin import nested

from .models import Option, Question, Survey, Submission, Answer


class OptionInline(nested.NestedTabularInline):
    model = Option
    extra = 2  # تعداد گزینه‌های پیش‌فرض


class QuestionInline(nested.NestedTabularInline):
    model = Question
    extra = 1
    inlines = [OptionInline]


@admin.register(Survey)
class SurveyAdmin(nested.NestedModelAdmin):
    list_display = ["title", "is_active", "created_at"]
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "text",
        "survey",
        "question_type",
        "is_required",
        "order",
    )
    list_filter = (
        "survey",
        "question_type",
        "is_required",
    )
    search_fields = ("text",)
    ordering = ("survey", "order")


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = (
        "text",
        "question",
        "order",
    )
    list_filter = ("question",)
    search_fields = ("text",)
    ordering = ("question", "order")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "survey",
        "user",
        "created_at",
    )
    list_filter = (
        "survey",
        "created_at",
    )
    search_fields = (
        "user__phone_number",
        "user__first_name",
        "user__last_name",
        "survey__title",
    )
    ordering = ("-created_at",)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = (
        "question",
        "submission",
        "text_answer",
    )
    list_filter = (
        "question",
        "submission__survey",
    )
    search_fields = (
        "question__text",
        "text_answer",
        "submission__user__phone_number",
        "submission__user__first_name",
        "submission__user__last_name",
    )
    filter_horizontal = ("selected_options",)