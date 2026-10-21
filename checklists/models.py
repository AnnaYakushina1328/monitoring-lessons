from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from visits.models import Visit


class ChecklistTemplate(models.Model):
    code = models.SlugField(
        "Код",
        max_length=50,
        unique=True,
    )

    name = models.CharField(
        "Название",
        max_length=500,
    )

    max_score = models.PositiveSmallIntegerField(
        "Максимальный балл",
    )

    is_active = models.BooleanField(
        "Активен",
        default=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "шаблон чек-листа"
        verbose_name_plural = "шаблоны чек-листов"

    def __str__(self):
        return self.name


class ChecklistSection(models.Model):
    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.CASCADE,
        related_name="sections",
        verbose_name="Шаблон",
    )

    order = models.PositiveSmallIntegerField(
        "Порядок",
    )

    title = models.CharField(
        "Название блока",
        max_length=255,
    )

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "order"],
                name="unique_checklist_section_order",
            ),
        ]
        verbose_name = "блок чек-листа"
        verbose_name_plural = "блоки чек-листа"

    def __str__(self):
        return f"{self.order}. {self.title}"


class ChecklistCriterion(models.Model):
    section = models.ForeignKey(
        ChecklistSection,
        on_delete=models.CASCADE,
        related_name="criteria",
        verbose_name="Блок",
    )

    order = models.PositiveSmallIntegerField(
        "Порядок",
    )

    title = models.CharField(
        "Критерий",
        max_length=500,
    )

    comment_hint = models.CharField(
        "Подсказка к комментарию",
        max_length=500,
        blank=True,
    )

    class Meta:
        ordering = [
            "section__order",
            "order",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "order"],
                name="unique_criterion_order",
            ),
        ]
        verbose_name = "критерий"
        verbose_name_plural = "критерии"

    def __str__(self):
        return self.title

    @property
    def max_score(self):
        teacher_max = (
            self.options
            .filter(side=ChecklistOption.Side.TEACHER)
            .aggregate(value=models.Max("score"))["value"]
            or 0
        )

        student_max = (
            self.options
            .filter(side=ChecklistOption.Side.STUDENT)
            .aggregate(value=models.Max("score"))["value"]
            or 0
        )

        return teacher_max + student_max


class ChecklistOption(models.Model):
    class Side(models.TextChoices):
        TEACHER = "teacher", "Деятельность преподавателя"
        STUDENT = "student", "Деятельность студента"

    criterion = models.ForeignKey(
        ChecklistCriterion,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name="Критерий",
    )

    side = models.CharField(
        "Сторона",
        max_length=20,
        choices=Side.choices,
    )

    order = models.PositiveSmallIntegerField(
        "Порядок",
    )

    score = models.PositiveSmallIntegerField(
        "Балл",
    )

    text = models.TextField(
        "Описание",
    )

    class Meta:
        ordering = [
            "criterion",
            "side",
            "order",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "criterion",
                    "side",
                    "order",
                ],
                name="unique_checklist_option",
            ),
        ]
        verbose_name = "вариант оценки"
        verbose_name_plural = "варианты оценки"

    def __str__(self):
        return f"{self.score}: {self.text[:80]}"


class ChecklistLevel(models.Model):
    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.CASCADE,
        related_name="levels",
        verbose_name="Шаблон",
    )

    order = models.PositiveSmallIntegerField(
        "Порядок",
    )

    name = models.CharField(
        "Уровень",
        max_length=100,
    )

    min_score = models.PositiveSmallIntegerField(
        "От",
    )

    max_score = models.PositiveSmallIntegerField(
        "До",
    )

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "order"],
                name="unique_checklist_level_order",
            ),
        ]
        verbose_name = "уровень результата"
        verbose_name_plural = "уровни результатов"

    def __str__(self):
        return f"{self.name}: {self.min_score}–{self.max_score}"


class Assessment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        COMPLETED = "completed", "Завершён"

    visit = models.OneToOneField(
        Visit,
        on_delete=models.CASCADE,
        related_name="assessment",
        verbose_name="Посещение",
    )

    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.PROTECT,
        related_name="assessments",
        verbose_name="Чек-лист",
    )

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    general_comment = models.TextField(
        "Общие выводы и рекомендации",
        blank=True,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_assessments",
        verbose_name="Последнее изменение",
    )

    created_at = models.DateTimeField(
        "Создан",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "Изменён",
        auto_now=True,
    )

    completed_at = models.DateTimeField(
        "Завершён",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "оценивание занятия"
        verbose_name_plural = "оценивания занятий"

    def __str__(self):
        return f"{self.visit} — {self.template}"

    @property
    def total_score(self):
        total = 0

        for answer in self.answers.select_related(
            "teacher_option",
            "student_option",
        ):
            if answer.teacher_option:
                total += answer.teacher_option.score

            if answer.student_option:
                total += answer.student_option.score

        return total

    @property
    def level(self):
        score = self.total_score

        return (
            self.template.levels
            .filter(
                min_score__lte=score,
                max_score__gte=score,
            )
            .first()
        )


class AssessmentAnswer(models.Model):
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Оценивание",
    )

    criterion = models.ForeignKey(
        ChecklistCriterion,
        on_delete=models.PROTECT,
        related_name="answers",
        verbose_name="Критерий",
    )

    teacher_option = models.ForeignKey(
        ChecklistOption,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Оценка деятельности преподавателя",
    )

    student_option = models.ForeignKey(
        ChecklistOption,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Оценка деятельности студента",
    )

    comment = models.TextField(
        "Комментарий эксперта",
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "criterion"],
                name="unique_assessment_criterion",
            ),
        ]
        verbose_name = "ответ чек-листа"
        verbose_name_plural = "ответы чек-листа"

    def clean(self):
        errors = {}

        if self.teacher_option:
            if (
                self.teacher_option.criterion_id
                != self.criterion_id
                or self.teacher_option.side
                != ChecklistOption.Side.TEACHER
            ):
                errors["teacher_option"] = (
                    "Выбранный вариант не относится "
                    "к деятельности преподавателя этого критерия."
                )

        if self.student_option:
            if (
                self.student_option.criterion_id
                != self.criterion_id
                or self.student_option.side
                != ChecklistOption.Side.STUDENT
            ):
                errors["student_option"] = (
                    "Выбранный вариант не относится "
                    "к деятельности студента этого критерия."
                )

        if errors:
            raise ValidationError(errors)


class AssessmentAcknowledgement(models.Model):
    class Decision(models.TextChoices):
        AGREE = "agree", "Ознакомлен, согласен"
        DISAGREE = "disagree", "Ознакомлен, не согласен"

    assessment = models.OneToOneField(
        Assessment,
        on_delete=models.CASCADE,
        related_name="acknowledgement",
        verbose_name="??????????",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="?????????????",
    )
    decision = models.CharField(
        "???????",
        max_length=20,
        choices=Decision.choices,
    )
    comment = models.TextField(
        "??????????? ?????????????",
        blank=True,
    )
    created_at = models.DateTimeField(
        "???? ????????????",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "???????????? ? ???????????"
        verbose_name_plural = "???????????? ? ????????????"
