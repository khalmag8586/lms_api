from django.db import models
from django.conf import settings
import uuid

class EduSystem(models.Model):
    id=models.UUIDField(default=uuid.uuid4,primary_key=True,editable=False)
    name=models.CharField(max_length=255,unique=True)
    name_ar=models.CharField(max_length=255,unique=True)
    description=models.TextField(blank=True,null=True)
    is_active=models.BooleanField(default=True)
    is_deleted=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_created_edusystem",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_updated_edusystem",
        blank=True,
        null=True,
    )
    