from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from openpyxl import load_workbook

from teachers.models import Teacher


def clean_value(value):
    if value is None:
        return ""

    return " ".join(str(value).strip().split())


class Command(BaseCommand):
    help = "Импорт преподавателей из файла Excel"

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            type=str,
            help="Путь к файлу .xlsx",
        )

        parser.add_argument(
            "--sheet",
            type=str,
            default=None,
            help="Название листа. Если не указано, используется активный лист.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.exists():
            raise CommandError(
                f"Файл не найден: {file_path}"
            )

        try:
            workbook = load_workbook(
                file_path,
                read_only=True,
                data_only=True,
            )
        except Exception as exc:
            raise CommandError(
                f"Не удалось открыть Excel-файл: {exc}"
            )

        sheet_name = options["sheet"]

        if sheet_name:
            if sheet_name not in workbook.sheetnames:
                raise CommandError(
                    f"Лист '{sheet_name}' не найден."
                )

            worksheet = workbook[sheet_name]
        else:
            worksheet = workbook.active

        header_row = None

        for row_number in range(
            1,
            min(worksheet.max_row, 30) + 1,
        ):
            employee_header = clean_value(
                worksheet.cell(row=row_number, column=1).value
            )

            position_header = clean_value(
                worksheet.cell(row=row_number, column=4).value
            )

            if (
                employee_header.lower() == "сотрудник"
                and "должност" in position_header.lower()
            ):
                header_row = row_number
                break

        if header_row is None:
            raise CommandError(
                "Не удалось найти заголовки "
                "'Сотрудник' и 'Должность'."
            )

        created_count = 0
        updated_count = 0
        skipped_count = 0

        seen_names = set()

        for row_number in range(
            header_row + 1,
            worksheet.max_row + 1,
        ):
            full_name = clean_value(
                worksheet.cell(
                    row=row_number,
                    column=1,
                ).value
            )

            position = clean_value(
                worksheet.cell(
                    row=row_number,
                    column=4,
                ).value
            )

            if not full_name:
                skipped_count += 1
                continue

            normalized_name = full_name.casefold()

            if normalized_name in seen_names:
                self.stdout.write(
                    self.style.WARNING(
                        f"Дубликат в Excel: {full_name}"
                    )
                )
                skipped_count += 1
                continue

            seen_names.add(normalized_name)

            teacher, created = Teacher.objects.update_or_create(
                full_name=full_name,
                defaults={
                    "position": position,
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        workbook.close()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Импорт завершён."
            )
        )

        self.stdout.write(
            f"Создано: {created_count}"
        )

        self.stdout.write(
            f"Обновлено: {updated_count}"
        )

        self.stdout.write(
            f"Пропущено: {skipped_count}"
        )

        self.stdout.write(
            f"Всего преподавателей в базе: "
            f"{Teacher.objects.count()}"
        )
