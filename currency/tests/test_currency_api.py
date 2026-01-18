from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from currency.models import CurrencyExchange, UserBalance


CURRENCY_LIST_URL = reverse("currencies:currency-list")
HISTORY_LIST_URL = reverse("currencies:history-list")
REGISTER_LIST_URL = reverse("currencies:register-list")
BALANCE_LIST_URL = reverse("currencies:balance-list")


class AuthenticatedApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="testuser",
            password="12345678"
        )
        UserBalance.objects.create(user=self.user, balance=1000)

        self.client.force_authenticate(user=self.user)


class UnauthenticatedCurrencyApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_currency_list_auth_required(self):
        res = self.client.get(CURRENCY_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCurrencyApiTests(AuthenticatedApiTestCase):
    def test_currency_exchange_post_success(self):
        payload = {"currency_code": "USD"}

        res = self.client.post(CURRENCY_LIST_URL, data=payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["currency_code"], "USD")
        self.assertEqual(UserBalance.objects.get(user=self.user).balance, 999)

    def test_currency_code_required(self):
        payload = {"currency_code": ""}

        res = self.client.post(CURRENCY_LIST_URL, data=payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data["currency_code"],
            "currency code is required"
        )

    def test_currency_limit(self):
        for _ in range(1500):
            CurrencyExchange.objects.create(
                user=self.user,
                currency_code="USD",
                rate=41.5,
            )

        payload = {"currency_code": "EUR"}

        res = self.client.post(CURRENCY_LIST_URL, data=payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["error"], "Monthly request limit reached")

    @patch("currency.views.get_exchange_rate")
    def test_currency_exchange_wrong_code(self, mock_rate):
        mock_rate.side_effect = ValidationError(
            {"currency_code": "Invalid currency code"}
        )
        payload = {"currency_code": "123"}
        res = self.client.post(CURRENCY_LIST_URL, data=payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("currency_code", res.data)

    def test_currency_not_enough_money(self):
        UserBalance.objects.filter(user=self.user).update(balance=0)

        payload = {"currency_code": "USD"}

        res = self.client.post(CURRENCY_LIST_URL, data=payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["detail"], "Not enough money")


class UnauthenticatedHistoryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_currency_list_auth_required(self):
        res = self.client.get(HISTORY_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedHistoryApiTests(AuthenticatedApiTestCase):
    def setUp(self):
        super().setUp()

        self.record1 = CurrencyExchange.objects.create(
            user=self.user,
            currency_code="EUR",
            rate=50,
            created_at=timezone.now()
        )
        self.record2 = CurrencyExchange.objects.create(
            user=self.user,
            currency_code="USD",
            rate=41.5,
            created_at=timezone.now()
        )
        self.record3 = CurrencyExchange.objects.create(
            user=self.user,
            currency_code="EUR",
            rate=50,
            created_at=timezone.now()
        )

    def test_history_list_get_success(self):
        res = self.client.get(HISTORY_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)

    def test_history_filter_by_currency(self):
        res = self.client.get(HISTORY_LIST_URL, {"currency_code": "EUR"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]["currency_code"], "EUR")

    def test_history_filter_by_date(self):
        today = timezone.now().date().isoformat()

        res = self.client.get(HISTORY_LIST_URL, {"created_at": today})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)

    def test_history_list_user_isolation(self):
        user1 = User.objects.create(
            username="example",
            password="pass12331",
        )
        CurrencyExchange.objects.create(
            user=user1,
            currency_code="EUR",
            rate=50,
            created_at=timezone.now()
        )

        res = self.client.get(HISTORY_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)


class RegisterApiTests(TestCase):
    def test_register_success(self):
        payload = {
            "username": "testuser",
            "password": "pass12331",
        }

        res = self.client.post(REGISTER_LIST_URL, data=payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["user"]["username"], "testuser")
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_register_duplicate_username(self):
        User.objects.create(
            username="testuser",
            password="pass12331",
        )

        payload = {
            "username": "testuser",
            "password": "pass12331",
        }

        res = self.client.post(REGISTER_LIST_URL, data=payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_too_short(self):
        payload = {
            "username": "testuser",
            "password": "pass",
        }

        res = self.client.post(REGISTER_LIST_URL, data=payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class UnauthenticatedBalanceApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_currency_list_auth_required(self):
        res = self.client.get(BALANCE_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBalanceApiTests(AuthenticatedApiTestCase):
    def test_balance_list_success(self):
        res = self.client.get(BALANCE_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["balance"], 1000)

    def test_balance_list_user_isolation(self):
        user1 = User.objects.create(
            username="example",
            password="pass12331",
        )
        UserBalance.objects.filter(user=user1).update(balance=500)

        res = self.client.get(BALANCE_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["balance"], 1000)
