from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.customer_login, name='login'),
    path('register/', views.register_view, name='register'),
    path('restaurant-login/', views.restaurant_login, name='restaurant_login'),
    path('restaurant-register/', views.restaurant_register_view, name='restaurant_register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('profile/', views.profile_view, name='profile'),
]