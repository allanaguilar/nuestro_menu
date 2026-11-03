from django.contrib import admin

from apps.chores.models import Chore


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ("title", "household", "cadence", "assignee", "done_on")
    list_filter = ("cadence",)
