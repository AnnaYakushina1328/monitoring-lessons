from django.contrib import admin

from .models import Visit


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = (
        "teacher",
        "date",
        "lesson_number",
        "subject",
        "group",
        "format",
        "status",
    )

    list_filter = (
        "status",
        "format",
        "date",
        "is_open_lesson",
    )

    search_fields = (
        "teacher__full_name",
        "subject",
        "group",
        "room",
        "topic",
    )

    filter_horizontal = (
        "auditors",
    )

    ordering = (
        "-date",
        "lesson_number",
    )

    date_hierarchy = "date"
