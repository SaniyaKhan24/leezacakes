import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AccountVerificationToken, Address

User = get_user_model()


def _notify(subject, body, recipient):
    transaction.on_commit(lambda: send_mail(subject, body, None, [recipient], fail_silently=True))


@transaction.atomic
def register_user(**data):
    password = data.pop("password")
    data.pop("password_confirm", None)
    user = User.objects.create_user(password=password, **data)
    issue_verification_token(user)
    return user


def login_user(email, password):
    user = authenticate(email=email.strip().lower(), password=password)
    if not user or not user.is_active or not user.is_email_verified:
        raise AuthenticationFailed("Invalid credentials.")
    refresh = RefreshToken.for_user(user)
    return user, refresh


def issue_verification_token(user):
    raw = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    AccountVerificationToken.objects.filter(
        user=user, purpose=AccountVerificationToken.PURPOSE_EMAIL, used_at__isnull=True
    ).update(used_at=timezone.now())
    record = AccountVerificationToken.objects.create(
        user=user,
        purpose=AccountVerificationToken.PURPOSE_EMAIL,
        token_digest=digest,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    _notify("Verify your Leeza Cakes email", f"Verification token: {raw}", user.email)
    return record, raw


@transaction.atomic
def confirm_email(uid, raw_token):
    try:
        user_id = urlsafe_base64_decode(uid).decode()
        digest = hashlib.sha256(raw_token.encode()).hexdigest()
        record = (
            AccountVerificationToken.objects.select_for_update()
            .select_related("user")
            .get(
                user_id=user_id,
                token_digest=digest,
                purpose=AccountVerificationToken.PURPOSE_EMAIL,
                used_at__isnull=True,
            )
        )
    except (ValueError, TypeError, AccountVerificationToken.DoesNotExist):
        raise ValidationError(  # nosec B105 - validation text, not a credential
            {"token": "Invalid or expired verification token."}  # nosec B105
        ) from None
    if record.expires_at <= timezone.now():
        raise ValidationError(  # nosec B105 - validation text, not a credential
            {"token": "Invalid or expired verification token."}  # nosec B105
        )
    record.used_at = timezone.now()
    record.save(update_fields=("used_at",))
    user = record.user
    user.is_email_verified = True
    user.save(update_fields=("is_email_verified",))
    return user


@transaction.atomic
def change_password(user, current_password, new_password):
    if not user.check_password(current_password):
        raise ValidationError(  # nosec B105 - validation text, not a credential
            {"current_password": "Current password is incorrect."}  # nosec B105
        )
    user.set_password(new_password)
    user.save(update_fields=("password",))
    _notify("Your Leeza Cakes password changed", "Your password was changed.", user.email)
    return user


def request_password_reset(email):
    user = User.objects.filter(email__iexact=email.strip().lower(), is_active=True).first()
    if user:
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        _notify("Reset your Leeza Cakes password", f"Reset uid: {uid}; token: {token}", user.email)


@transaction.atomic
def confirm_password_reset(uid, token, new_password):
    try:
        user_id = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=user_id, is_active=True)
    except (ValueError, TypeError, User.DoesNotExist):
        raise ValidationError(  # nosec B105 - validation text, not a credential
            {"token": "Invalid or expired reset token."}  # nosec B105
        ) from None
    if not default_token_generator.check_token(user, token):
        raise ValidationError(  # nosec B105 - validation text, not a credential
            {"token": "Invalid or expired reset token."}  # nosec B105
        )
    user.set_password(new_password)
    user.save(update_fields=("password",))
    _notify("Your Leeza Cakes password was reset", "Your password was reset.", user.email)
    return user


@transaction.atomic
def create_address(user, **data):
    is_default = data.pop("is_default", False)
    if is_default:
        Address.objects.filter(user=user, is_default=True).update(is_default=False)
    return Address.objects.create(user=user, is_default=is_default, **data)


@transaction.atomic
def update_address(address, **data):
    is_default = data.pop("is_default", address.is_default)
    if is_default:
        Address.objects.filter(user=address.user, is_default=True).exclude(pk=address.pk).update(
            is_default=False
        )
    for key, value in data.items():
        setattr(address, key, value)
    address.is_default = is_default
    address.save()
    return address


@transaction.atomic
def set_default_address(address):
    Address.objects.filter(user=address.user, is_default=True).exclude(pk=address.pk).update(
        is_default=False
    )
    address.is_default = True
    address.save(update_fields=("is_default", "updated_at"))
    return address
