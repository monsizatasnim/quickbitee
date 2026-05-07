from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'email',
        'first_name', 'last_name',
        'is_customer', 'is_restaurant_owner',
        'is_staff'
    )
    list_filter = ('is_customer', 'is_restaurant_owner', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('QuickBite Info', {
            'fields': (
                'is_customer',
                'is_restaurant_owner',
                'phone_number',
                'address',
                'allergies',
                'profile_picture',
            )
        }),
    )