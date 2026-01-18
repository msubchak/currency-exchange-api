from django.db import models
from django.contrib.auth.models import User


class CurrencyExchange(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="exchanges"
    )
    currency_code = models.CharField(max_length=50)
    rate = models.DecimalField(max_digits=10, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)


class UserBalance(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="balance"
    )
    balance = models.IntegerField(default=1000)
