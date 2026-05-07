from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    is_customer = models.BooleanField(default=True)
    is_restaurant_owner = models.BooleanField(default=False)

    # Customer profile fields
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.username

    def has_complete_profile(self):
        """Check if customer has filled required info"""
        return bool(self.phone_number and self.address)