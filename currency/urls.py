from django.urls import path, include
from rest_framework import routers

from currency.views import RegisterViewSet, BalanceViewSet, HistoryViewSet, CurrencyViewSet

app_name = "currencies"

router = routers.DefaultRouter()

router.register("currency", CurrencyViewSet, basename="currency")
router.register("history", HistoryViewSet, basename="history")
router.register("register", RegisterViewSet, basename="register")
router.register("balance", BalanceViewSet, basename="balance")

urlpatterns = [
    path("", include(router.urls))
]
