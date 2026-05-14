from django.db import models
from django.conf import settings
from restaurants.models import MenuItem, Restaurant
import uuid


class GroupOrder(models.Model):
    name = models.CharField(max_length=100)
    invite_code = models.CharField(max_length=8, unique=True, blank=True)
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE,
        null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_groups'
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='group_orders',
        blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    main_order = models.OneToOneField(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='group_order'
    )

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def get_total_members(self):
        return self.members.count()

    def __str__(self):
        return self.name

class GroupOrderItem(models.Model):
    PAYMENT_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('BKASH', 'Bkash'),
        ('NAGAD', 'Nagad'),
    ]

    group = models.ForeignKey(
        GroupOrder, on_delete=models.CASCADE,
        related_name='group_items'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES,
        default='COD'
    )

    def get_subtotal(self):
        return self.menu_item.price * self.quantity

    def __str__(self):
        return f"{self.user.username} - {self.menu_item.name}"


class GroupMemberPayment(models.Model):
    """Tracks each member's payment status in a group"""
    PAYMENT_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('BKASH', 'Bkash'),
        ('NAGAD', 'Nagad'),
    ]

    group = models.ForeignKey(
        GroupOrder, on_delete=models.CASCADE,
        related_name='member_payments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    food_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    delivery_share = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES,
        default='COD'
    )
    is_paid = models.BooleanField(default=False)
    transaction_id = models.CharField(
        max_length=20, blank=True, null=True
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.group.name} - {'Paid' if self.is_paid else 'Unpaid'}"