from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.permissions import (
    can_create_visit,
    visible_visits_for,
)

from teachers.models import Teacher


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

    from visits.models import Visit

    context = {

        "teacher_count": (
            Teacher.objects
            .filter(
                is_active=True
            )
            .count()
        ),

        "visit_count": (
            visits.count()
        ),

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
    }

    return render(
        request,
        "core/home.html",
        context,
    )
