from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):

    is_customer = models.BooleanField(default=True)
    is_restaurant_owner = models.BooleanField(default=False)

    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.username