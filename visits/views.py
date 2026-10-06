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


def get_schedule_warnings(visit):
    """
    Информационные предупреждения о других посещениях
    в тот же день.

    Ничего не блокирует.
    """

    other_visits = (
        Visit.objects
        .filter(
            date=visit.date,
        )
        .exclude(
            pk=visit.pk,
        )
        .exclude(
            status=Visit.Status.CANCELLED,
        )
        .select_related(
            "teacher",
        )
        .prefetch_related(
            "auditors",
            "methodists",
        )
    )

    warnings = []


    # --------------------------------------------------------
    # Преподаватель
    # --------------------------------------------------------

    teacher_visits = [
        item
        for item in other_visits
        if item.teacher_id == visit.teacher_id
    ]

    if teacher_visits:

        lessons = []

        for item in teacher_visits:

            if item.lesson_number:
                lessons.append(
                    f"{item.lesson_number} занятие"
                )
            else:
                lessons.append(
                    "занятие без номера"
                )

        warnings.append(
            (
                f"На {visit.date.strftime('%d.%m.%Y')} "
                f"у преподавателя "
                f"{visit.teacher.full_name} "
                f"уже есть другое посещение: "
                + ", ".join(lessons)
                + "."
            )
        )


    # --------------------------------------------------------
    # Эксперты
    # --------------------------------------------------------

    selected_auditors = list(
        visit.auditors.all()
    )

    for auditor in selected_auditors:

        matches = [
            item
            for item in other_visits
            if item.auditors.filter(
                pk=auditor.pk
            ).exists()
        ]

        if matches:

            warnings.append(
                (
                    f"Эксперт {auditor} "
                    f"уже назначен на другое посещение "
                    f"{visit.date.strftime('%d.%m.%Y')}."
                )
            )


    # --------------------------------------------------------
    # Методисты
    # --------------------------------------------------------

    selected_methodists = list(
        visit.methodists.all()
    )

    for methodist in selected_methodists:

        matches = [
            item
            for item in other_visits
            if item.methodists.filter(
                pk=methodist.pk
            ).exists()
        ]

        if matches:

            warnings.append(
                (
                    f"Методист {methodist} "
                    f"уже назначен на другое посещение "
                    f"{visit.date.strftime('%d.%m.%Y')}."
                )
            )


    return warnings


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
            "auditors",
            "methodists",
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
            "auditors",
            "methodists",
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
        visit.checklist_code
    )


    assessment_mismatch = (
        assessment is not None
        and assessment.template.code
        != expected_template_code
    )


    checklist_label = (
        visit.get_checklist_code_display()
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
            "У вас нет прав на планирование посещений."
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


            for warning in get_schedule_warnings(
                visit
            ):
                messages.warning(
                    request,
                    warning,
                )


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
            "У вас нет прав на "
            "редактирование посещений."
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


            for warning in get_schedule_warnings(
                visit
            ):
                messages.warning(
                    request,
                    warning,
                )


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
            "У вас нет прав на отмену посещений."
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
