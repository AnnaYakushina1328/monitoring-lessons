from django.core.management.base import BaseCommand
from django.db import transaction

from checklists.models import Assessment
from visits.models import Visit


class Command(BaseCommand):
    help = (
        "Удаляет тестовые оценивания, шаблон которых "
        "не соответствует формату посещения"
    )

    def handle(self, *args, **options):
        mismatched = []

        for assessment in Assessment.objects.select_related(
            "visit",
            "template",
        ):
            expected = (
                "online"
                if assessment.visit.format == Visit.Format.ONLINE
                else "oup"
            )

            if assessment.template.code != expected:
                mismatched.append(assessment)

        if not mismatched:
            self.stdout.write(
                self.style.SUCCESS(
                    "Несоответствующих оцениваний нет."
                )
            )
            return

        with transaction.atomic():
            for assessment in mismatched:
                visit = assessment.visit

                self.stdout.write(
                    f"Сброс: посещение #{visit.pk} "
                    f"({visit.get_format_display()}) "
                    f"{assessment.template.code}"
                )

                assessment.delete()

                visit.status = Visit.Status.PLANNED
                visit.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Удалено тестовых оцениваний: "
                f"{len(mismatched)}"
            )
        )
