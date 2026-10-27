from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


class Blog(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()

    media = models.FileField(
        upload_to="blogs/"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


@receiver(post_delete, sender=Blog)
def delete_blog_media_file(sender, instance, **kwargs):
    if instance.media:
        instance.media.delete(save=False)