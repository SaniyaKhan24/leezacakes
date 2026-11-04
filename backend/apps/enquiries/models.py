import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.accounts.validators import validate_phone


def reference_for(enquiry_id):
    return f"ENQ-{enquiry_id.hex[:6].upper()}"


class Enquiry(models.Model):
    GENERAL = "general"
    CUSTOM_CAKE = "custom_cake"
    KIND_CHOICES = ((GENERAL, "General"), (CUSTOM_CAKE, "Custom cake"))
    NEW = "new"
    CONTACTED = "contacted"
    CLOSED = "closed"
    STATUS_CHOICES = ((NEW, "New"), (CONTACTED, "Contacted"), (CLOSED, "Closed"))
    MESSAGE_MAX_LENGTH = 2000

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=16, db_index=True, editable=False)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=GENERAL)
    name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True, validators=[validate_phone])
    occasion = models.CharField(max_length=120, blank=True)
    event_date = models.DateField(null=True, blank=True)
    servings = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(1000)]
    )
    budget = models.CharField(max_length=60, blank=True)
    message = models.TextField(max_length=MESSAGE_MAX_LENGTH)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "id")
        verbose_name_plural = "enquiries"
        indexes = [models.Index(fields=("status", "created_at"))]

    def __str__(self):
        return f"{self.reference} {self.name}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = reference_for(self.id)
        super().save(*args, **kwargs)
