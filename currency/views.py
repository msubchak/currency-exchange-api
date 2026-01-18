import os
import requests
from django.core.exceptions import PermissionDenied
from django.db import transaction
from datetime import date
from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from currency.models import CurrencyExchange, UserBalance
from currency.serializers import (
    CurrencyExchangeSerializer,
    RegisterSerializer,
    BalanceSerializer,
    HistorySerializer)
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("EXCHANGE_API_KEY")


def get_exchange_rate(currency_code: str) -> float:
    URL = (
        f"https://v6.exchangerate-api.com/v6/{API_KEY}"
        f"/pair/{currency_code.upper()}/UAH"
    )

    try:
        response = requests.get(URL)
        data = response.json()
    except requests.exceptions.RequestException:
        raise APIException("External exchange service is unavailable.")

    if data.get("result") != "success":
        error_type = data.get("error-type", "unknown_error")
        raise ValidationError({
            "currency_code": f"Invalid currency "
                             f"code or API error: {error_type}"
        })

    return data.get("conversion_rate")


class CurrencyViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = CurrencyExchangeSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return CurrencyExchange.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        user = self.request.user
        currency_code = request.data.get("currency_code", "").upper()

        if not currency_code:
            raise ValidationError(
                {"currency_code": "currency code is required"}
            )

        today = date.today()
        limit = CurrencyExchange.objects.filter(
            user=self.request.user,
            created_at__year=today.year,
            created_at__month=today.month,
        ).count()
        if limit >= 1500:
            raise ValidationError(
                {"error": "Monthly request limit reached"},
                code=429
            )

        balance = UserBalance.objects.get(user=self.request.user)
        if balance.balance <= 0:
            raise PermissionDenied("Not enough money")

        rate = get_exchange_rate(currency_code)

        with transaction.atomic():
            balance.balance -= 1
            balance.save()

            currency = CurrencyExchange.objects.create(
                user=user,
                currency_code=currency_code,
                rate=rate,
            )

        serializer = self.get_serializer(currency)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class HistoryViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = HistorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = CurrencyExchange.objects.all()

        queryset = queryset.filter(user=user)

        currency = self.request.query_params.get("currency_code")
        date_param = self.request.query_params.get("created_at")

        if currency:
            queryset = queryset.filter(currency_code=currency)

        if date_param:
            queryset = queryset.filter(created_at__date=date_param)

        return queryset


class RegisterViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            "user": {
                "username": user.username,
            },
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "message": "User registered successfully."
        }, status=status.HTTP_201_CREATED)


class BalanceViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = BalanceSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return UserBalance.objects.filter(user=self.request.user)
