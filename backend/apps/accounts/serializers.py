from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Address
from .validators import normalize_phone, validate_phone

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_email_verified",
            "date_joined",
        )
        read_only_fields = ("id", "email", "is_email_verified", "date_joined")

    phone_number = serializers.CharField(
        required=False, allow_blank=True, validators=[validate_phone]
    )

    def validate_phone_number(self, value):
        return normalize_phone(value)


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(
        required=False, allow_blank=True, validators=[validate_phone]
    )

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}  # nosec B105
            )
        from django.contrib.auth.password_validation import validate_password

        validate_password(attrs["password"])
        attrs["phone_number"] = normalize_phone(attrs.get("phone_number", ""))
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError(
                {"email": "An account with this email already exists."}
            )
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}  # nosec B105
            )
        from django.contrib.auth.password_validation import validate_password

        validate_password(attrs["new_password"], self.context["request"].user)
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}  # nosec B105
            )
        from django.contrib.auth.password_validation import validate_password

        validate_password(attrs["new_password"])
        return attrs


class VerificationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)


class VerificationConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "id",
            "label",
            "recipient_name",
            "phone_number",
            "address_line_1",
            "address_line_2",
            "locality",
            "city",
            "state",
            "postal_code",
            "country_code",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    phone_number = serializers.CharField(validators=[validate_phone])

    def validate_country_code(self, value):
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError("Use a two-letter country code.")
        return value

    def validate(self, attrs):
        for field in (
            "label",
            "recipient_name",
            "address_line_1",
            "locality",
            "city",
            "state",
            "postal_code",
        ):
            if field in attrs and not attrs[field].strip():
                raise serializers.ValidationError({field: "This field may not be blank."})
        attrs["phone_number"] = normalize_phone(attrs.get("phone_number", ""))
        return attrs
