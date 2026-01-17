import os
import requests
from django.db import transaction
from datetime import date
from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from currency.models import CurrencyExchange, UserBalance
from currency.serializers import CurrencyExchangeSerializer, RegisterSerializer, BalanceSerializer, HistorySerializer
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("EXCHANGE_API_KEY")


def get_exchange_rate(currency_code: str) -> float:
    pass


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
            return Response(
                {"error": "currency code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = date.today()
        limit = CurrencyExchange.objects.filter(user=self.request.user, created_at__date=today).count()
        if limit > 100:
            return Response(
                {"error": "Daily request limit reached"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        balance = UserBalance.objects.get(user=self.request.user)
        if balance.balance <= 0:
            return Response(
                {"error": "Not enough money"},
                status=status.HTTP_403_FORBIDDEN
            )

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
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        date = self.request.query_params.get("created_at")

        if currency:
            queryset = queryset.filter(currency_code=currency)

        if date:
            queryset = queryset.filter(created_at__date=date)

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
