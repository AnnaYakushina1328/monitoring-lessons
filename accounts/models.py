from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Администратор"
        METHODIST = "methodist", "Методист"
        EXPERT = "expert", "Эксперт"
        TEACHER = "teacher", "Преподаватель"

    role = models.CharField(
        "Роль",
        max_length=20,
        choices=Role.choices,
        default=Role.EXPERT,
    )

    def __str__(self):
        return self.get_full_name() or self.username
