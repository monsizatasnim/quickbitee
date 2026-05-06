from django.contrib import admin
from .models import GroupOrder, GroupOrderItem

admin.site.register(GroupOrder)
admin.site.register(GroupOrderItem)