from django.urls import path
from . import views

app_name = 'group_order'

urlpatterns = [
    path('', views.group_list, name='group_list'),
    path('create/', views.create_group, name='create_group'),
    path('join/', views.join_group, name='join_group'),
    path('<int:group_id>/', views.group_detail, name='group_detail'),
    path('remove-item/<int:item_id>/', views.remove_group_item, name='remove_group_item'),
    path('<int:group_id>/pay/', views.group_pay, name='group_pay'),
    path('<int:group_id>/pay/confirm/', views.group_pay_confirm, name='group_pay_confirm'),
    path('<int:group_id>/payment-summary/', views.group_payment_summary, name='group_payment_summary'),
]