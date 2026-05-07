from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_order, name='create_order'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path('my/', views.my_orders, name='my_orders'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('pay/<int:order_id>/', views.make_payment, name='make_payment'),
path('admin-orders/', views.admin_orders, name='admin_orders'),
path('admin-orders/<int:order_id>/update/', views.update_order_status, name='update_order_status'),
]