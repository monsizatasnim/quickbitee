
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('add-to-cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
]