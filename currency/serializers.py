from django.contrib.auth.models import User
from rest_framework import serializers
from currency.models import CurrencyExchange, UserBalance


class CurrencyExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyExchange
        fields = (
            "id",
            "currency_code",
            "rate",
            "created_at"
        )
        read_only_fields = (
            "id",
            "rate",
            "created_at"
        )


class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyExchange
        fields = (
            "id",
            "currency_code",
            "rate",
            "created_at"
        )


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = (
            "username",
            "password",
        )

    def create(self, validated_data):
        user = User.objects.create_user(
            password=validated_data["password"],
            username=validated_data["username"]
        )

        UserBalance.objects.create(user=user)

        return user


class BalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBalance
        fields = ("balance",)
