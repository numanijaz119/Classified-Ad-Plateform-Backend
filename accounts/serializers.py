from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import User
import uuid


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone",
            "password",
            "password_confirm",
        )

    def validate_email(self, value):
        """Validate email format and uniqueness."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Password fields didn't match."}
            )

        # Validate password strength
        try:
            validate_password(data["password"])
        except ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})

        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User.objects.create_user(password=password, **validated_data)

        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField()
    password = serializers.CharField(
        style={"input_type": "password"}, trim_whitespace=False
    )

    def validate_email(self, value):
        """Normalize email to lowercase."""
        return value.lower()

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        if email and password:
            user = authenticate(
                request=self.context.get("request"), username=email, password=password
            )

            if not user:
                raise serializers.ValidationError(
                    "Invalid email or password.", code="authorization"
                )

            if not user.is_active:
                raise serializers.ValidationError(
                    "User account is disabled.", code="account_disabled"
                )

            if not user.email_verified:
                raise serializers.ValidationError(
                    "Please verify your email address before logging in.",
                    code="email_not_verified",
                )

            if user.is_suspended:
                raise serializers.ValidationError(
                    "Your account has been suspended. Please contact support.",
                    code="account_suspended",
                )

            data["user"] = user
        else:
            raise serializers.ValidationError(
                'Must include "email" and "password".', code="required"
            )

        return data


class GoogleLoginSerializer(serializers.Serializer):
    """Serializer for Google OAuth login."""

    id_token = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile data."""

    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "avatar",
            "full_name",
            "email_verified",
            "is_active",
            "show_email",
            "show_phone",
            "email_notifications",
            "email_message_notifications",
            "created_at",
            "updated_at",
            "google_id",
            "is_staff",
            "is_superuser",
        )
        read_only_fields = (
            "id",
            "email",
            "email_verified",
            "created_at",
            "updated_at",
            "is_staff",
            "is_superuser",
        )


class UserPublicSerializer(serializers.ModelSerializer):
    """Public user info respecting privacy settings."""

    full_name = serializers.CharField(source="get_full_name", read_only=True)
    email = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "avatar", "email", "phone", "email_verified"]

    def get_email(self, obj):
        """Return email only if user allows it."""
        if obj.show_email:
            return obj.email
        return None

    def get_phone(self, obj):
        """Return phone only if user allows it."""
        if obj.show_phone:
            return obj.phone
        return None


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "phone",
            "avatar",
            "show_email",
            "show_phone",
            "email_notifications",
            "email_message_notifications",
        )

    def validate_first_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("First name is required.")
        return value.strip()

    def validate_last_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Last name is required.")
        return value.strip()

    def validate_avatar(self, value):
        if value:
            # Check file size (max 2MB)
            if value.size > 2 * 1024 * 1024:
                raise serializers.ValidationError("Avatar file size cannot exceed 2MB.")

            # Check file type
            allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Invalid file type. Allowed: JPEG, PNG, GIF, WEBP."
                )
        return value


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""

    code = serializers.CharField(max_length=6, min_length=6)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Code must be 6 digits.")
        return value


class ResendVerificationSerializer(serializers.Serializer):
    """Serializer for resending verification code."""

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower()


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request."""

    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.lower()
        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                raise serializers.ValidationError("This account is not active.")
            if user.is_suspended:
                raise serializers.ValidationError("This account has been suspended.")
        except User.DoesNotExist:
            # Don't reveal if email exists for security
            pass
        return email


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset with code."""

    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_email(self, value):
        return value.lower()

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Code must be 6 digits.")
        return value

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Password fields didn't match."}
            )

        # Validate password strength
        try:
            validate_password(data["new_password"])
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": e.messages})

        return data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        required=False
    )  # Optional for social users
    new_password = serializers.CharField(min_length=8, validators=[validate_password])
    confirm_password = serializers.CharField()

    def validate(self, attrs):
        user = self.context["request"].user

        # Check if user logged in via Google (no password set)
        if user.google_id and not user.has_usable_password():
            # Social login user setting password for first time
            if attrs.get("current_password"):
                raise serializers.ValidationError(
                    {
                        "current_password": "You signed up with Google. No current password needed."
                    }
                )
        else:
            # Regular user must provide current password
            if not attrs.get("current_password"):
                raise serializers.ValidationError(
                    {"current_password": "Current password is required."}
                )

            # Verify current password
            if not user.check_password(attrs["current_password"]):
                raise serializers.ValidationError(
                    {"current_password": "Current password is incorrect."}
                )

        # Validate password confirmation
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        return attrs


class UserPrivacySettingsSerializer(serializers.ModelSerializer):
    """Serializer specifically for privacy settings."""

    class Meta:
        model = User
        fields = ("show_email", "show_phone", "email_notifications")
