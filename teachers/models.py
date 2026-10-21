from django.db import models


class Teacher(models.Model):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teacher_profile",
        verbose_name="Учётная запись",
        limit_choices_to={"role": "teacher"},
    )
    full_name = models.CharField(
        "ФИО",
        max_length=255,
        unique=True,
        db_index=True,
    )

    position = models.CharField(
        "Должность",
        max_length=255,
        blank=True,
    )

    is_active = models.BooleanField(
        "Работает",
        default=True,
    )

    created_at = models.DateTimeField(
        "Создан",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "Изменён",
        auto_now=True,
    )

    class Meta:
        ordering = ["full_name"]
        verbose_name = "преподаватель"
        verbose_name_plural = "преподаватели"

    def __str__(self):
        return self.full_name
