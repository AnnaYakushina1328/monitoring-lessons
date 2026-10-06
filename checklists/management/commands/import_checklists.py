import re
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from openpyxl import load_workbook

from checklists.models import (
    ChecklistCriterion,
    ChecklistLevel,
    ChecklistOption,
    ChecklistSection,
    ChecklistTemplate,
)


SHEETS = {
    "Чек-лист ПД": {
        "code": "pd",
    },

    "Чек-лист ЛПЗ": {
        "code": "lpz",
    },

    "Чек-лист ОУП": {
        "code": "oup",
    },

    "Чек-лист УП и ПП": {
        "code": "uppp",
    },

    "Чек-лист аттестации": {
        "code": "attestation",
    },

    "Чек-лист онлайн-занятия": {
        "code": "online",
    },
}


LEVEL_NAMES = {
    "высок": "Высокая эффективность",
    "достат": "Достаточная эффективность",
    "удовлетвор": "Удовлетворительная эффективность",
    "низк": "Низкая эффективность",
}


# ============================================================
# Методисты подтвердили:
# онлайн-чек-лист = 59 баллов.
#
# Исходная книга местами содержит старые 57,
# хотя сумма допустимых вариантов = 59.
# ============================================================

ONLINE_LEVELS = [
    (
        "Высокая эффективность",
        53,
        59,
    ),
    (
        "Достаточная эффективность",
        46,
        52,
    ),
    (
        "Удовлетворительная эффективность",
        39,
        45,
    ),
    (
        "Низкая эффективность",
        0,
        38,
    ),
]


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def clean_section_title(value):
    value = clean(value)

    value = re.sub(
        r"^(?:Блок\s*)?\d+\.\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )

    return value.rstrip(".").strip()


def parse_option(value):

    value = clean(value)

    if not value:
        return None

    if value.lower().startswith(
        "не оценивается"
    ):
        return None

    match = re.match(
        r"^\s*(\d+)\s*[:\-]\s*(.*)$",
        value,
        flags=re.DOTALL,
    )

    if not match:
        return None

    score = int(
        match.group(1)
    )

    text = (
        match.group(2)
        .strip()
    )

    return {
        "score": score,
        "text": text,
    }


def get_level_name(text):

    lowered = text.lower()

    for key, name in LEVEL_NAMES.items():

        if key in lowered:
            return name

    return None


def parse_levels(ws):

    levels = []

    for row in ws.iter_rows(
        values_only=True
    ):

        text = clean(
            row[0]
        )

        match = re.match(
            r"^(\d+)\s*[–-]\s*(\d+)\s*бал",
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        first = int(
            match.group(1)
        )

        second = int(
            match.group(2)
        )

        name = get_level_name(
            text
        )

        if not name:
            continue

        levels.append(
            {
                "name": name,
                "min_score": min(
                    first,
                    second,
                ),
                "max_score": max(
                    first,
                    second,
                ),
            }
        )

    return levels


def parse_sheet(ws):

    rows = list(
        ws.iter_rows(
            values_only=True
        )
    )


    # --------------------------------------------------------
    # Название формы
    # --------------------------------------------------------

    template_name = clean(
        rows[0][0]
    )


    # --------------------------------------------------------
    # Ищем строку таблицы:
    # № | Критерий | Деятельность...
    # --------------------------------------------------------

    header_index = None

    for index, row in enumerate(
        rows
    ):

        if clean(
            row[1]
        ) == "Критерий":

            header_index = index
            break


    if header_index is None:
        raise CommandError(
            f"{ws.title}: "
            "не найдена таблица критериев."
        )


    sections = []

    current_section = None
    current_criterion = None


    for row in rows[
        header_index + 1:
    ]:

        col_a = clean(
            row[0]
        )

        col_b = clean(
            row[1]
        )


        # ----------------------------------------------------
        # Конец таблицы
        # ----------------------------------------------------

        if col_a.upper().startswith(
            "ИТОГО БАЛЛОВ"
        ):
            break


        # ----------------------------------------------------
        # Строка итога блока
        # ----------------------------------------------------

        if col_a.lower().startswith(
            "итого по"
        ):
            current_criterion = None
            continue


        # ----------------------------------------------------
        # Новый блок
        # ----------------------------------------------------

        is_section = (
            bool(col_a)
            and bool(col_b)
            and (
                col_a.lower().startswith(
                    "блок "
                )
                or bool(
                    re.match(
                        r"^\d+\.\s*",
                        col_a,
                    )
                )
            )
        )


        if is_section:

            current_section = {
                "title": (
                    clean_section_title(
                        col_a
                    )
                ),
                "criteria": [],
            }

            sections.append(
                current_section
            )

            current_criterion = None


        # ----------------------------------------------------
        # Новый критерий
        # ----------------------------------------------------

        if col_b:

            if current_section is None:
                continue

            current_criterion = {
                "title": col_b,

                "comment_hint": clean(
                    row[8]
                ),

                "teacher_options": [],

                "student_options": [],
            }

            current_section[
                "criteria"
            ].append(
                current_criterion
            )


        if current_criterion is None:
            continue


        # ----------------------------------------------------
        # Вариант преподавателя
        # ----------------------------------------------------

        teacher_option = parse_option(
            row[2]
        )

        if teacher_option:

            current_criterion[
                "teacher_options"
            ].append(
                teacher_option
            )


        # ----------------------------------------------------
        # Вариант студента
        # ----------------------------------------------------

        student_option = parse_option(
            row[4]
        )

        if student_option:

            current_criterion[
                "student_options"
            ].append(
                student_option
            )


    # --------------------------------------------------------
    # Максимумы считаем ИЗ ВАРИАНТОВ.
    #
    # Это принципиально:
    # в исходной книге есть расхождения между
    # строками "Итого" и самими вариантами.
    # --------------------------------------------------------

    max_score = 0


    for section in sections:

        section_max = 0

        for criterion in section[
            "criteria"
        ]:

            teacher_max = max(
                (
                    option["score"]
                    for option
                    in criterion[
                        "teacher_options"
                    ]
                ),
                default=0,
            )

            student_max = max(
                (
                    option["score"]
                    for option
                    in criterion[
                        "student_options"
                    ]
                ),
                default=0,
            )

            criterion[
                "max_score"
            ] = (
                teacher_max
                + student_max
            )

            section_max += (
                criterion[
                    "max_score"
                ]
            )


        section[
            "max_score"
        ] = section_max

        max_score += (
            section_max
        )


    levels = parse_levels(
        ws
    )


    return {
        "name": template_name,

        "sections": sections,

        "max_score": max_score,

        "levels": levels,
    }


class Command(BaseCommand):

    help = (
        "Импортирует все типы чек-листов "
        "из исходной книги Колледжа."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "--file",
            default=(
                "data/import/"
                "checklists.xlsx"
            ),
        )


    def handle(
        self,
        *args,
        **options,
    ):

        source = Path(
            options["file"]
        )


        if not source.exists():

            raise CommandError(
                f"Файл не найден: {source}"
            )


        workbook = load_workbook(
            source,
            data_only=False,
        )


        self.stdout.write("")


        for sheet_name, config in (
            SHEETS.items()
        ):

            if sheet_name not in workbook.sheetnames:

                raise CommandError(
                    f"Нет листа: {sheet_name}"
                )


            ws = workbook[
                sheet_name
            ]

            data = parse_sheet(
                ws
            )

            code = config[
                "code"
            ]


            # ------------------------------------------------
            # Коррекция онлайн-чек-листа
            # ------------------------------------------------

            if code == "online":

                if data[
                    "max_score"
                ] != 59:

                    raise CommandError(
                        "Онлайн-чек-лист должен "
                        "давать 59 баллов по "
                        "вариантам критериев. "
                        f"Получено: "
                        f"{data['max_score']}"
                    )

                data[
                    "levels"
                ] = [
                    {
                        "name": name,
                        "min_score": minimum,
                        "max_score": maximum,
                    }
                    for (
                        name,
                        minimum,
                        maximum,
                    )
                    in ONLINE_LEVELS
                ]


            template, created = (
                ChecklistTemplate.objects
                .get_or_create(
                    code=code,
                    defaults={
                        "name": (
                            data["name"]
                        ),
                        "max_score": (
                            data[
                                "max_score"
                            ]
                        ),
                        "is_active": True,
                    },
                )
            )


            has_results = (
                template.assessments
                .exists()
            )


            # ------------------------------------------------
            # Если этот шаблон уже использовался,
            # структуру НЕ перестраиваем:
            # старые ответы должны остаться привязаны
            # к прежним Criterion / Option.
            # ------------------------------------------------

            if has_results:

                template.name = (
                    data["name"]
                )

                template.is_active = True


                # Онлайн 59 — согласованная правка.
                if code == "online":

                    template.max_score = 59


                    # Levels не имеют FK из Assessment,
                    # поэтому их можно безопасно исправить.
                    template.levels.all().delete()


                    for (
                        level_order,
                        level,
                    ) in enumerate(
                        data["levels"],
                        start=1,
                    ):

                        ChecklistLevel.objects.create(
                            template=template,
                            order=level_order,
                            name=level["name"],
                            min_score=(
                                level[
                                    "min_score"
                                ]
                            ),
                            max_score=(
                                level[
                                    "max_score"
                                ]
                            ),
                        )


                template.save(
                    update_fields=[
                        "name",
                        "max_score",
                        "is_active",
                    ]
                )


                criteria_count = (
                    ChecklistCriterion.objects
                    .filter(
                        section__template=(
                            template
                        )
                    )
                    .count()
                )


                self.stdout.write(
                    self.style.WARNING(
                        f"{code}: "
                        "уже используется — "
                        "структура сохранена; "
                        f"{template.sections.count()} "
                        "блоков, "
                        f"{criteria_count} критериев, "
                        f"max={template.max_score}"
                    )
                )

                continue


            # ------------------------------------------------
            # Новый / ещё не использовавшийся шаблон:
            # можно безопасно собрать заново.
            # ------------------------------------------------

            template.name = (
                data["name"]
            )

            template.max_score = (
                data["max_score"]
            )

            template.is_active = True

            template.save()


            template.sections.all().delete()

            template.levels.all().delete()


            option_count = 0
            criterion_count = 0


            for (
                section_order,
                section_data,
            ) in enumerate(
                data["sections"],
                start=1,
            ):

                section = (
                    ChecklistSection.objects
                    .create(
                        template=template,
                        order=section_order,
                        title=(
                            section_data[
                                "title"
                            ]
                        ),
                    )
                )


                for (
                    criterion_order,
                    criterion_data,
                ) in enumerate(
                    section_data[
                        "criteria"
                    ],
                    start=1,
                ):

                    criterion = (
                        ChecklistCriterion.objects
                        .create(
                            section=section,
                            order=criterion_order,
                            title=(
                                criterion_data[
                                    "title"
                                ]
                            ),
                            comment_hint=(
                                criterion_data[
                                    "comment_hint"
                                ]
                            ),
                        )
                    )


                    criterion_count += 1


                    for (
                        option_order,
                        option,
                    ) in enumerate(
                        criterion_data[
                            "teacher_options"
                        ],
                        start=1,
                    ):

                        ChecklistOption.objects.create(
                            criterion=criterion,
                            side=(
                                ChecklistOption
                                .Side
                                .TEACHER
                            ),
                            order=option_order,
                            score=option[
                                "score"
                            ],
                            text=option[
                                "text"
                            ],
                        )

                        option_count += 1


                    for (
                        option_order,
                        option,
                    ) in enumerate(
                        criterion_data[
                            "student_options"
                        ],
                        start=1,
                    ):

                        ChecklistOption.objects.create(
                            criterion=criterion,
                            side=(
                                ChecklistOption
                                .Side
                                .STUDENT
                            ),
                            order=option_order,
                            score=option[
                                "score"
                            ],
                            text=option[
                                "text"
                            ],
                        )

                        option_count += 1


            for (
                level_order,
                level,
            ) in enumerate(
                data["levels"],
                start=1,
            ):

                ChecklistLevel.objects.create(
                    template=template,
                    order=level_order,
                    name=level["name"],
                    min_score=(
                        level[
                            "min_score"
                        ]
                    ),
                    max_score=(
                        level[
                            "max_score"
                        ]
                    ),
                )


            self.stdout.write(
                self.style.SUCCESS(
                    f"{code}: "
                    f"{len(data['sections'])} блоков, "
                    f"{criterion_count} критериев, "
                    f"{option_count} вариантов, "
                    f"max={data['max_score']}"
                )
            )


        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Импорт чек-листов завершён."
            )
        )
