# restaurants/urls.py

from django.urls import path
from . import views

app_name = 'restaurants'

urlpatterns = [
    # Public
    path('', views.restaurant_list, name='restaurant_list'),
    path('<int:pk>/', views.restaurant_detail, name='restaurant_detail'),

    # Owner Dashboard
    path('dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('dashboard/edit/', views.edit_restaurant, name='edit_restaurant'),
    path('dashboard/add-item/', views.add_menu_item, name='add_menu_item'),
    path('dashboard/edit-item/<int:item_id>/', views.edit_menu_item, name='edit_menu_item'),
    path('dashboard/delete-item/<int:item_id>/', views.delete_menu_item, name='delete_menu_item'),
    path('dashboard/order/<int:order_id>/update/', views.update_order_status, name='update_order_status'),
]