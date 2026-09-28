from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from core.permissions import (
    can_create_visit,
    can_edit_assessment,
    can_view_visit,
    visible_visits_for,
)

from .forms import VisitForm
from .models import Visit


@login_required
def visit_list(request):

    visits = (
        visible_visits_for(
            request.user
        )
        .select_related(
            "teacher"
        )
        .prefetch_related(
            "auditors"
        )
        .order_by(
            "-date",
            "-lesson_number",
            "-id",
        )
    )

    return render(
        request,
        "visits/list.html",
        {
            "visits": visits,
            "can_create_visits": (
                can_create_visit(
                    request.user
                )
            ),
        },
    )


@login_required
def visit_detail(
    request,
    pk,
):
    visit = get_object_or_404(
        Visit.objects
        .select_related(
            "teacher",
            "assessment__template",
        )
        .prefetch_related(
            "auditors"
        ),
        pk=pk,
    )

    if not can_view_visit(
        request.user,
        visit,
    ):
        raise PermissionDenied(
            "У вас нет доступа к этому посещению."
        )

    assessment = getattr(
        visit,
        "assessment",
        None,
    )

    expected_template_code = (
        "online"
        if visit.format
        == Visit.Format.ONLINE
        else "oup"
    )

    assessment_mismatch = (
        assessment is not None
        and assessment.template.code
        != expected_template_code
    )

    checklist_label = (
        "Онлайн-чек-лист"
        if visit.format
        == Visit.Format.ONLINE
        else "Чек-лист ОУП"
    )

    return render(
        request,
        "visits/detail.html",
        {
            "visit": visit,
            "assessment": assessment,

            "assessment_mismatch": (
                assessment_mismatch
            ),

            "checklist_label": (
                checklist_label
            ),

            "can_edit_checklist": (
                can_edit_assessment(
                    request.user,
                    visit,
                )
            ),
        },
    )


@login_required
def visit_create(request):

    if not can_create_visit(
        request.user
    ):
        raise PermissionDenied(
            "Планировать посещения может "
            "только администратор."
        )

    if request.method == "POST":

        form = VisitForm(
            request.POST
        )

        if form.is_valid():

            visit = form.save(
                commit=False
            )

            visit.created_by = (
                request.user
            )

            visit.save()

            form.save_m2m()

            return redirect(
                "visits:detail",
                pk=visit.pk,
            )

    else:
        form = VisitForm()

    return render(
        request,
        "visits/create.html",
        {
            "form": form,
        },
    )
