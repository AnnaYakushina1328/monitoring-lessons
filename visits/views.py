from django.contrib import messages
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

    can_manage_visit = (
        can_create_visit(
            request.user
        )
    )

    can_cancel_visit = (
        can_manage_visit
        and visit.status
        not in (
            Visit.Status.COMPLETED,
            Visit.Status.CANCELLED,
        )
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

            "can_manage_visit": (
                can_manage_visit
            ),

            "can_cancel_visit": (
                can_cancel_visit
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

            messages.success(
                request,
                "Посещение успешно создано.",
            )

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


@login_required
def visit_edit(
    request,
    pk,
):
    if not can_create_visit(
        request.user
    ):
        raise PermissionDenied(
            "Редактировать посещения может "
            "только администратор."
        )

    visit = get_object_or_404(
        Visit,
        pk=pk,
    )

    if request.method == "POST":

        form = VisitForm(
            request.POST,
            instance=visit,
        )

        if form.is_valid():

            visit = form.save()

            messages.success(
                request,
                "Изменения сохранены.",
            )

            return redirect(
                "visits:detail",
                pk=visit.pk,
            )

    else:

        form = VisitForm(
            instance=visit,
        )

    return render(
        request,
        "visits/edit.html",
        {
            "form": form,
            "visit": visit,
        },
    )


@login_required
def visit_cancel(
    request,
    pk,
):
    if not can_create_visit(
        request.user
    ):
        raise PermissionDenied(
            "Отменять посещения может "
            "только администратор."
        )

    visit = get_object_or_404(
        Visit.objects.select_related(
            "teacher"
        ),
        pk=pk,
    )

    if visit.status == Visit.Status.COMPLETED:

        messages.error(
            request,
            (
                "Завершённое посещение нельзя отменить. "
                "Результат уже зафиксирован."
            ),
        )

        return redirect(
            "visits:detail",
            pk=visit.pk,
        )

    if visit.status == Visit.Status.CANCELLED:

        messages.info(
            request,
            "Посещение уже отменено.",
        )

        return redirect(
            "visits:detail",
            pk=visit.pk,
        )

    if request.method == "POST":

        visit.status = (
            Visit.Status.CANCELLED
        )

        visit.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        messages.success(
            request,
            "Посещение отменено.",
        )

        return redirect(
            "visits:detail",
            pk=visit.pk,
        )

    return render(
        request,
        "visits/cancel.html",
        {
            "visit": visit,
        },
    )
