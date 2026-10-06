from django.conf import settings
from django.db import models

from teachers.models import Teacher


class Visit(models.Model):
    class Format(models.TextChoices):
        IN_PERSON = "in_person", "Очно"
        ONLINE = "online", "Онлайн"

    class ChecklistType(models.TextChoices):
        PD = (
            "pd",
            "Теоретическое занятие (ПД)",
        )

        LPZ = (
            "lpz",
            "Лабораторно-практическое занятие (ЛПЗ)",
        )

        OUP = (
            "oup",
            "Общеобразовательное занятие (ОУП)",
        )

        UPPP = (
            "uppp",
            "Учебная / производственная практика",
        )

        ATTESTATION = (
            "attestation",
            "Аттестация студентов",
        )

        ONLINE = (
            "online",
            "Онлайн-занятие",
        )


    class Status(models.TextChoices):
        PLANNED = "planned", "Запланировано"
        IN_PROGRESS = "in_progress", "Проводится"
        COMPLETED = "completed", "Завершено"
        CANCELLED = "cancelled", "Отменено"

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="visits",
        verbose_name="Преподаватель",
    )

    date = models.DateField(
        "Дата посещения",
        db_index=True,
    )

    lesson_number = models.PositiveSmallIntegerField(
        "Номер занятия",
        null=True,
        blank=True,
        choices=[(number, str(number)) for number in range(1, 9)],
    )

    subject = models.CharField(
        "Дисциплина",
        max_length=255,
    )

    group = models.CharField(
        "Группа",
        max_length=100,
        blank=True,
    )

    room = models.CharField(
        "Аудитория",
        max_length=100,
        blank=True,
    )

    topic = models.CharField(
        "Тема занятия",
        max_length=500,
        blank=True,
    )

    purpose = models.TextField(
        "Цель посещения",
        blank=True,
    )

    format = models.CharField(
        "Формат",
        max_length=20,
        choices=Format.choices,
        default=Format.IN_PERSON,
    )

    checklist_code = models.CharField(
        "Тип чек-листа",
        max_length=30,
        choices=ChecklistType.choices,
        default=ChecklistType.OUP,
        db_index=True,
    )


    auditors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="assigned_visits",
        verbose_name="Эксперты",
        blank=True,
    )

    methodists = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="Методисты",
        related_name="methodist_visits",
        blank=True,
    )


    is_open_lesson = models.BooleanField(
        "Открытое занятие",
        default=False,
    )

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        db_index=True,
    )

    notes = models.TextField(
        "Примечание",
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_visits",
        verbose_name="Кто создал",
    )

    created_at = models.DateTimeField(
        "Создано",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "Изменено",
        auto_now=True,
    )

    class Meta:
        ordering = ["date", "lesson_number", "teacher__full_name"]
        verbose_name = "посещение"
        verbose_name_plural = "посещения"

    @property
    def lesson_label(self):
        if not self.lesson_number:
            return "—"

        return f"{self.lesson_number}-я пара"



    def __str__(self):
        return f"{self.teacher} — {self.date}"
