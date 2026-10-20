import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    username = None
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=32, blank=True)
    is_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.email


class Address(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=80)
    recipient_name = models.CharField(max_length=160)
    phone_number = models.CharField(max_length=32)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    locality = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=24)
    country_code = models.CharField(max_length=2, default="IN")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-is_default", "-created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(is_default=True),
                name="one_default_address_per_user",
            )
        ]

    def __str__(self):
        return f"{self.label} - {self.recipient_name}"


class AccountVerificationToken(models.Model):
    PURPOSE_EMAIL = "email_verification"
    PURPOSES = ((PURPOSE_EMAIL, "Email verification"),)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="verification_tokens"
    )
    purpose = models.CharField(max_length=40, choices=PURPOSES)
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=("user", "purpose", "expires_at"))]

    def __str__(self):
        return f"{self.user.email} ({self.purpose})"
