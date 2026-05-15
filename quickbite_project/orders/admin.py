from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model  = OrderItem
    extra = 0
    readonly_fields = ('menu_item', 'quantity', 'price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'restaurant',
        'status', 'total_price',
        'payment_method', 'is_paid',
        'created_at'
    )
    list_filter = ('status', 'payment_method', 'is_paid', 'restaurant')
    search_fields = ('user__username',   'restaurant__name')
    inlines = [OrderItemInline]