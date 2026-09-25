from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Мониторинг",
            {
                "fields": (
                    "role",
                )
            },
        ),
    )

    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            "Мониторинг",
            {
                "fields": (
                    "role",
                )
            },
        ),
    )

    list_display = (
        "username",
        "get_full_name",
        "role",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_active",
    )

    @admin.display(description="ФИО")
    def get_full_name(self, obj):
        return obj.get_full_name() or "—"
