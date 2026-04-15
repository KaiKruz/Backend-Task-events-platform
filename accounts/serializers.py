from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import AccountRole
from accounts.services import normalize_email

User = get_user_model()


def _reject_username_field(serializer: serializers.Serializer) -> None:
    data = getattr(serializer, "initial_data", None)
    if isinstance(data, dict) and "username" in data:
        raise serializers.ValidationError(
            {"username": "This field is not allowed."},
            code="invalid",
        )


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=AccountRole.choices)

    def validate(self, attrs):
        _reject_username_field(self)
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(write_only=True, min_length=6, max_length=6)

    def validate(self, attrs):
        _reject_username_field(self)
        if not attrs["otp"].isdigit():
            raise serializers.ValidationError({"otp": "OTP must be 6 digits."})
        return attrs


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("username", None)

    def validate(self, attrs):
        _reject_username_field(self)
        email = normalize_email(attrs["email"])
        password = attrs["password"]

        user = (
            User.objects.filter(email__iexact=email)
            .select_related("account_profile")
            .first()
        )
        if user is None or not user.check_password(password):
            raise AuthenticationFailed(
                detail="Invalid email or password.",
                code="invalid_credentials",
            )

        if not user.account_profile.email_verified:
            raise AuthenticationFailed(
                detail="Email address is not verified.",
                code="email_not_verified",
            )

        refresh = self.get_token(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
