from django.contrib import admin

from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "position",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "is_active",
        "position",
    )

    search_fields = (
        "full_name",
        "position",
    )

    ordering = ("full_name",)

    list_per_page = 50
