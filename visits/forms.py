from django import forms

from accounts.models import User

from .models import Visit


VISIT_PURPOSE_CHOICES = [
    (
        "",
        "— Выберите цель посещения —",
    ),
    (
        "Оценка методики проведения занятия в соответствии с его видом",
        "Методика проведения занятия",
    ),
    (
        "Оценка степени формирования профессиональных компетенций (ПК) у обучающихся через выполнение практических задач и работу с реальным оборудованием/ПО.",
        "Формирование профессиональных компетенций (ПК)",
    ),
    (
        "Оценка интеграции теоретических знаний в практическую деятельность (умение обучающихся применять теорию для решения прикладных задач)",
        "Интеграция теории в практическую деятельность",
    ),
    (
        "Оценка эффективности использования современного оборудования, тренажеров, симуляторов или специализированного программного обеспечения в практической подготовке",
        "Использование оборудования, тренажеров и ПО",
    ),
    (
        "Оценка эффективности использования электронной информационно-образовательной среды (ЭИОС, МЭШ) и цифровых образовательных ресурсов в ходе учебного занятия",
        "Использование ЭИОС, МЭШ и цифровых ресурсов",
    ),
    (
        "Оценка объективности системы текущего контроля и промежуточной аттестации обучающихся (соответствие критериев оценивания фонду оценочных средств)",
        "Текущий контроль и промежуточная аттестация",
    ),
]


class VisitForm(forms.ModelForm):


    purpose = forms.ChoiceField(
        label="Цель посещения",
        choices=VISIT_PURPOSE_CHOICES,
        required=False,
    )


    class Meta:
        model = Visit

        fields = [
            "teacher",
            "date",
            "lesson_number",
            "subject",
            "group",
            "room",
            "topic",
            "purpose",
            "format",
            "checklist_code",
            "auditors",
            "methodists",
            "is_open_lesson",
            "notes",
        ]

        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),

            "topic": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),

            "purpose": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),

            "auditors": (
                forms.CheckboxSelectMultiple()
            ),

            "methodists": (
                forms.CheckboxSelectMultiple()
            ),
        }


    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )


        # HTML5 date принимает и отображает
        # значение только в формате YYYY-MM-DD.
        # Это предотвращает сброс даты
        # при редактировании посещения.
        self.fields["date"].widget.format = "%Y-%m-%d"
        self.fields["date"].input_formats = [
            "%Y-%m-%d",
        ]



        # ---------------------------------------------
        # Пара
        # ---------------------------------------------

        self.fields[
            "lesson_number"
        ].label = "Пара"

        self.fields[
            "lesson_number"
        ].choices = [
            ("", "— Выберите пару —"),
            (1, "1-я пара"),
            (2, "2-я пара"),
            (3, "3-я пара"),
            (4, "4-я пара"),
            (5, "5-я пара"),
            (6, "6-я пара"),
            (7, "7-я пара"),
            (8, "8-я пара"),
        ]


        # ---------------------------------------------
        # Эксперты
        # ---------------------------------------------

        self.fields[
            "auditors"
        ].queryset = (
            User.objects
            .filter(
                role=User.Role.EXPERT,
                is_active=True,
            )
            .order_by(
                "last_name",
                "first_name",
                "username",
            )
        )


        # ---------------------------------------------
        # Методисты
        # ---------------------------------------------

        self.fields[
            "methodists"
        ].queryset = (
            User.objects
            .filter(
                role=User.Role.METHODIST,
                is_active=True,
            )
            .order_by(
                "last_name",
                "first_name",
                "username",
            )
        )


    def clean_checklist_code(self):

        new_code = self.cleaned_data[
            "checklist_code"
        ]

        if not self.instance.pk:
            return new_code

        old_code = (
            Visit.objects
            .filter(
                pk=self.instance.pk
            )
            .values_list(
                "checklist_code",
                flat=True,
            )
            .first()
        )

        has_assessment = (
            Visit.objects
            .filter(
                pk=self.instance.pk,
                assessment__isnull=False,
            )
            .exists()
        )

        if (
            has_assessment
            and old_code != new_code
        ):
            raise forms.ValidationError(
                "Тип чек-листа нельзя изменить "
                "после начала оценивания."
            )

        return new_code


    def clean_format(self):

        new_format = self.cleaned_data[
            "format"
        ]

        if not self.instance.pk:
            return new_format

        try:
            self.instance.assessment
            has_assessment = True

        except Exception:
            has_assessment = False

        if (
            has_assessment
            and new_format
            != self.instance.format
        ):
            raise forms.ValidationError(
                "Формат нельзя изменить после начала "
                "заполнения чек-листа. "
                "Он определяет тип оценивания."
            )

        return new_format
