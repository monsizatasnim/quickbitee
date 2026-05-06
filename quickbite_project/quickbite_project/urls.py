from django.contrib import admin
from django.urls import path, include
from menu import views as menu_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('orders/', include('orders.urls')),
    path('menu/', include('menu.urls')),
    path('', menu_views.home, name='home'),
    path('groups/', include('group_order.urls')),
]