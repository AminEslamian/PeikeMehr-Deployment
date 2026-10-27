from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver




class Tag(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Report(models.Model):

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reports",
        null=True
    )

    text = models.TextField()

    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="reports"
    )

    # موضوع دلخواه (تگ «سایر») - به‌صورت یک Tag جدید ذخیره نمی‌شود
    other_tag = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report #{self.id} - {self.teacher}"


class ReportImage(models.Model):

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(
        upload_to="reports/images/"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Image for Report #{self.report_id}"


class ReportVideo(models.Model):

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="videos"
    )

    video = models.FileField(
        upload_to="reports/videos/",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Video for Report #{self.report_id}"


class Point(models.Model):

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="points",
        verbose_name="استاد",
    )

    score = models.IntegerField(
        verbose_name="امتیاز"
    )

    reason = models.TextField(
        verbose_name="دلیل"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ثبت"
    )

    def __str__(self):
        return f"{self.teacher} - {self.score}"

    class Meta:
        verbose_name = "امتیاز"
        verbose_name_plural = "امتیازات"
        ordering = ["-created_at"]
        
        
@receiver(post_delete, sender=ReportImage)
def delete_report_image_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


@receiver(post_delete, sender=ReportVideo)
def delete_report_video_file(sender, instance, **kwargs):
    if instance.video:
        instance.video.delete(save=False)
