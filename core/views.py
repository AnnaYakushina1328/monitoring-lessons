from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from checklists.models import Assessment
from core.permissions import (
    can_create_visit,
    can_view_monitoring,
    visible_visits_for,
)
from teachers.models import Teacher
from visits.models import Visit


def get_level_key(level):

    if not level:
        return "unknown"

    name = level.name.lower()

    if name.startswith("высок"):
        return "high"

    if name.startswith("достат"):
        return "sufficient"

    if name.startswith("удовлетвор"):
        return "satisfactory"

    if name.startswith("низк"):
        return "low"

    return "unknown"


@login_required
def home(request):

    visits = (
        visible_visits_for(
            request.user
        )
        .select_related(
            "teacher"
        )
    )

    context = {

        "teacher_count": (
            Teacher.objects
            .filter(
                is_active=True
            )
            .count()
        ),

        "visit_count": visits.count(),

        "planned_count": (
            visits
            .filter(
                status=Visit.Status.PLANNED
            )
            .count()
        ),

        "completed_count": (
            visits
            .filter(
                status=Visit.Status.COMPLETED
            )
            .count()
        ),

        "recent_visits": (
            visits
            .order_by(
                "-date",
                "-lesson_number",
                "-id",
            )[:6]
        ),

        "can_create_visits": (
            can_create_visit(
                request.user
            )
        ),

        "can_view_monitoring": (
            can_view_monitoring(
                request.user
            )
        ),
    }

    return render(
        request,
        "core/home.html",
        context,
    )


@login_required
def monitoring(request):

    if not can_view_monitoring(
        request.user
    ):
        raise PermissionDenied(
            "У вас нет доступа к разделу мониторинга."
        )


    # ========================================================
    # ФИЛЬТР
    # ========================================================

    format_filter = request.GET.get(
        "format",
        "all",
    )

    if format_filter not in (
        "all",
        Visit.Format.IN_PERSON,
        Visit.Format.ONLINE,
    ):
        format_filter = "all"


    queryset = (
        Assessment.objects
        .filter(
            status=Assessment.Status.COMPLETED
        )
        .select_related(
            "visit",
            "visit__teacher",
            "template",
        )
        .prefetch_related(
            "answers__teacher_option",
            "answers__student_option",
        )
    )


    if format_filter != "all":

        queryset = queryset.filter(
            visit__format=format_filter
        )


    assessments = list(
        queryset.order_by(
            "visit__teacher__full_name",
            "visit__date",
            "visit__lesson_number",
            "id",
        )
    )


    # ========================================================
    # РЕЗУЛЬТАТЫ
    # ========================================================

    result_rows = []

    teacher_results = defaultdict(
        list
    )

    percentages = []

    traffic_counts = {
        "high": 0,
        "sufficient": 0,
        "satisfactory": 0,
        "low": 0,
        "unknown": 0,
    }


    for assessment in assessments:

        score = assessment.total_score

        max_score = (
            assessment.template.max_score
            or 0
        )

        percent = (
            round(
                score
                / max_score
                * 100,
                1,
            )
            if max_score
            else 0
        )


        percentages.append(
            percent
        )


        level = assessment.level

        level_name = (
            level.name
            if level
            else "Без уровня"
        )

        level_key = get_level_key(
            level
        )


        traffic_counts[
            level_key
        ] += 1


        row = {
            "assessment": assessment,
            "score": score,
            "max_score": max_score,
            "percent": percent,
            "level_name": level_name,
            "level_key": level_key,
        }


        result_rows.append(
            row
        )


        teacher_results[
            assessment.visit.teacher_id
        ].append(
            row
        )


    # ========================================================
    # ОБЩАЯ СВОДКА
    # ========================================================

    total_completed = len(
        result_rows
    )


    average_percent = (
        round(
            sum(percentages)
            / len(percentages),
            1,
        )
        if percentages
        else 0
    )


    teacher_count = len(
        teacher_results
    )


    def share(count):

        if not total_completed:
            return 0

        return round(
            count
            / total_completed
            * 100,
            1,
        )


    def share_width(count):

        if not total_completed:
            return 0

        return round(
            count
            / total_completed
            * 100
        )


    traffic = {

        "high": {
            "count": traffic_counts["high"],
            "percent": share(
                traffic_counts["high"]
            ),
            "width": share_width(
                traffic_counts["high"]
            ),
        },

        "sufficient": {
            "count": traffic_counts["sufficient"],
            "percent": share(
                traffic_counts["sufficient"]
            ),
            "width": share_width(
                traffic_counts["sufficient"]
            ),
        },

        "satisfactory": {
            "count": traffic_counts["satisfactory"],
            "percent": share(
                traffic_counts["satisfactory"]
            ),
            "width": share_width(
                traffic_counts["satisfactory"]
            ),
        },

        "low": {
            "count": traffic_counts["low"],
            "percent": share(
                traffic_counts["low"]
            ),
            "width": share_width(
                traffic_counts["low"]
            ),
        },

        "unknown": {
            "count": traffic_counts["unknown"],
            "percent": share(
                traffic_counts["unknown"]
            ),
            "width": share_width(
                traffic_counts["unknown"]
            ),
        },
    }


    # ========================================================
    # ПРЕПОДАВАТЕЛИ
    # ========================================================

    teacher_rows = []


    for rows in teacher_results.values():

        rows.sort(
            key=lambda item: (
                item["assessment"].visit.date,
                item["assessment"].visit.lesson_number
                or 0,
                item["assessment"].pk,
            )
        )


        teacher = (
            rows[0]["assessment"]
            .visit
            .teacher
        )


        average = round(
            sum(
                item["percent"]
                for item in rows
            )
            / len(rows),
            1,
        )


        # ----------------------------------------------------
        # Динамика:
        # первое посещение -> третье посещение
        # ----------------------------------------------------

        dynamics = None

        if len(rows) >= 3:

            dynamics = round(
                rows[2]["percent"]
                - rows[0]["percent"],
                1,
            )


        counts = {
            "high": 0,
            "sufficient": 0,
            "satisfactory": 0,
            "low": 0,
            "unknown": 0,
        }


        for item in rows:

            counts[
                item["level_key"]
            ] += 1


        total = len(rows)


        def teacher_share(key):

            if not total:
                return 0

            return round(
                counts[key]
                / total
                * 100,
                1,
            )


        def teacher_width(key):

            if not total:
                return 0

            return round(
                counts[key]
                / total
                * 100
            )


        latest_result = rows[-1]


        teacher_rows.append(
            {
                "teacher": teacher,

                "count": total,

                "average_percent": (
                    average
                ),

                "dynamics": dynamics,

                # Цвет всей строки =
                # уровень последнего посещения
                "latest_level_key": (
                    latest_result[
                        "level_key"
                    ]
                ),

                "latest_level_name": (
                    latest_result[
                        "level_name"
                    ]
                ),

                # Текстовые проценты
                "high_percent": (
                    teacher_share(
                        "high"
                    )
                ),

                "sufficient_percent": (
                    teacher_share(
                        "sufficient"
                    )
                ),

                "satisfactory_percent": (
                    teacher_share(
                        "satisfactory"
                    )
                ),

                "low_percent": (
                    teacher_share(
                        "low"
                    )
                ),

                "unknown_percent": (
                    teacher_share(
                        "unknown"
                    )
                ),

                # ЦЕЛЫЕ значения именно для CSS width
                "high_width": (
                    teacher_width(
                        "high"
                    )
                ),

                "sufficient_width": (
                    teacher_width(
                        "sufficient"
                    )
                ),

                "satisfactory_width": (
                    teacher_width(
                        "satisfactory"
                    )
                ),

                "low_width": (
                    teacher_width(
                        "low"
                    )
                ),

                "unknown_width": (
                    teacher_width(
                        "unknown"
                    )
                ),
            }
        )


    teacher_rows.sort(
        key=lambda item: (
            item["teacher"].full_name
        )
    )


    # ========================================================
    # ПОСЛЕДНИЕ РЕЗУЛЬТАТЫ
    # ========================================================

    recent_results = sorted(
        result_rows,
        key=lambda item: (
            item["assessment"].visit.date,
            item["assessment"].visit.lesson_number
            or 0,
            item["assessment"].pk,
        ),
        reverse=True,
    )[:8]


    context = {

        "format_filter": (
            format_filter
        ),

        "total_completed": (
            total_completed
        ),

        "average_percent": (
            average_percent
        ),

        "teacher_count": (
            teacher_count
        ),

        "traffic": traffic,

        "teacher_rows": (
            teacher_rows
        ),

        "recent_results": (
            recent_results
        ),
    }


    return render(
        request,
        "core/monitoring.html",
        context,
    )



@login_required
def teacher_monitoring(
    request,
    teacher_id,
):

    if not can_view_monitoring(
        request.user
    ):
        raise PermissionDenied(
            "У вас нет доступа к разделу мониторинга."
        )


    from django.shortcuts import get_object_or_404


    teacher = get_object_or_404(
        Teacher,
        pk=teacher_id,
    )


    assessments = list(
        Assessment.objects
        .filter(
            status=Assessment.Status.COMPLETED,
            visit__teacher=teacher,
        )
        .select_related(
            "visit",
            "template",
        )
        .prefetch_related(
            "answers__teacher_option",
            "answers__student_option",
        )
        .order_by(
            "visit__date",
            "visit__lesson_number",
            "id",
        )
    )


    rows = []


    for index, assessment in enumerate(
        assessments,
        start=1,
    ):

        score = assessment.total_score

        max_score = (
            assessment.template.max_score
            or 0
        )

        percent = (
            round(
                score
                / max_score
                * 100,
                1,
            )
            if max_score
            else 0
        )


        level = assessment.level

        level_name = (
            level.name
            if level
            else "Без уровня"
        )

        level_key = get_level_key(
            level
        )


        rows.append(
            {
                "number": index,

                "assessment": assessment,

                "score": score,

                "max_score": max_score,

                "percent": percent,

                "level_name": level_name,

                "level_key": level_key,
            }
        )


    average_percent = (
        round(
            sum(
                item["percent"]
                for item in rows
            )
            / len(rows),
            1,
        )
        if rows
        else 0
    )


    dynamics = None

    if len(rows) >= 3:

        dynamics = round(
            rows[2]["percent"]
            - rows[0]["percent"],
            1,
        )


    return render(
        request,
        "core/teacher_monitoring.html",
        {
            "teacher": teacher,

            "rows": rows,

            "visit_count": len(
                rows
            ),

            "average_percent": (
                average_percent
            ),

            "dynamics": dynamics,
        },
    )


@login_required
def diagnostics(request):
    if not can_view_monitoring(request.user):
        raise PermissionDenied

    # Only completed assessments. Compare different templates by percentage.
    assessments = list(
        Assessment.objects.filter(status=Assessment.Status.COMPLETED)
        .select_related("template", "visit", "visit__teacher")
        .prefetch_related(
            "answers__teacher_option", "answers__student_option",
            "template__sections__criteria__options",
        )
    )
    selected_code = request.GET.get("checklist", "all")
    if selected_code != "all":
        assessments = [a for a in assessments if a.template.code == selected_code]

    statistics = {}
    for a in assessments:
        answers = {answer.criterion_id: answer for answer in a.answers.all()}
        for section in a.template.sections.all():
            score = 0
            maximum = 0
            for criterion in section.criteria.all():
                opts = list(criterion.options.all())
                teacher_max = max((o.score for o in opts if o.side == "teacher"), default=0)
                student_max = max((o.score for o in opts if o.side == "student"), default=0)
                maximum += teacher_max + student_max
                answer = answers.get(criterion.pk)
                if answer:
                    score += (answer.teacher_option.score if answer.teacher_option else 0)
                    score += (answer.student_option.score if answer.student_option else 0)
            if maximum == 0:
                continue
            # Section number provides stable comparison across checklist types;
            # use section names from real templates, never fabricated labels.
            item = statistics.setdefault(section.order, {
                "order": section.order, "title": section.title,
                "score": 0, "maximum": 0, "count": 0,
            })
            item["score"] += score
            item["maximum"] += maximum
            item["count"] += 1

    sections = sorted(statistics.values(), key=lambda item: item["order"])
    for item in sections:
        item["percent"] = round(item["score"] * 100 / item["maximum"], 1)
        item["width"] = min(100, max(0, item["percent"]))

    codes = sorted({a.template.code for a in Assessment.objects.filter(
        status=Assessment.Status.COMPLETED).select_related("template")})
    return render(request, "core/diagnostics.html", {
        "sections": sections, "total": len(assessments),
        "selected_code": selected_code, "codes": codes,
    })
