from django.urls import path
from . import views
app_name = 'group_order'

urlpatterns = [
    path('', views.group_list, name='group_list'),
    path('create/', views.create_group, name='create_group'),
    path('join/', views.join_group, name='join_group'),
    path('<int:group_id>/', views.group_detail, name='group_detail'),
    path('remove-item/<int:item_id>/', views.remove_group_item, name='remove_group_item'),
]