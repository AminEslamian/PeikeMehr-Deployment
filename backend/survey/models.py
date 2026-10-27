from django.conf import settings
from django.db import models


class QuestionType(models.TextChoices):
    TEXT = "text", "تشریحی"
    SINGLE_CHOICE = "single_choice", "تک گزینه‌ای (شامل دو گزینه‌ای)"
    MULTIPLE_CHOICE = "multiple_choice", "چند گزینه‌ای"


class Survey(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="questions"
    )
    text = models.CharField(max_length=500)
    question_type = models.CharField(
        max_length=20, choices=QuestionType.choices
    )
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.survey.title} - {self.text}"


class Option(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="options"
    )
    text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text


class Submission(models.Model):
    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="submissions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("survey", "user")

    def __str__(self):
        user_str = self.user.phone_number if self.user else "کاربر ناشناس"
        return f"{user_str} - {self.survey.title}"


class Answer(models.Model):
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text_answer = models.TextField(blank=True, null=True)
    selected_options = models.ManyToManyField(Option, blank=True)

    def __str__(self):
        return f"پاسخ به {self.question.text}"