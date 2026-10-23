from django.contrib import admin

from apps.shopping.models import ShoppingItem


@admin.register(ShoppingItem)
class ShoppingItemAdmin(admin.ModelAdmin):
    list_display = ("name", "household", "aisle", "done")
    list_filter = ("aisle", "done")
    search_fields = ("name",)
