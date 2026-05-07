from django.db import models
from django.conf import settings
from restaurants.models import MenuItem, Restaurant


class Order(models.Model):
    PAYMENT_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('BKASH', 'Bkash'),
        ('NAGAD', 'Nagad'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PREPARING', 'Preparing'),
        ('DELIVERED', 'Delivered'),
        ('CANCELED', 'Canceled'),
    ]

    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.SET_NULL,
        null=True, related_name='orders'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    delivery_charge = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES,
        default='COD'
    )
    customer_phone = models.CharField(max_length=15)
    customer_address = models.TextField()

    def grand_total(self):
        return self.total_price + self.delivery_charge

    def __str__(self):
        return f"Order #{self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def get_subtotal(self):
        return self.price * self.quantity