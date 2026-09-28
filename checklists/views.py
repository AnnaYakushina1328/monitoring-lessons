from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from visits.models import Visit

from .models import (
    Assessment,
    AssessmentAnswer,
    ChecklistCriterion,
    ChecklistOption,
    ChecklistSection,
    ChecklistTemplate,
)


def can_edit_visit(user, visit):
    if user.is_superuser:
        return True

    if user.role in (
        User.Role.ADMIN,
        User.Role.METHODIST,
    ):
        return True

    return visit.auditors.filter(
        pk=user.pk,
    ).exists()


def prepare_section(section, assessment):
    answers = {
        answer.criterion_id: answer
        for answer in assessment.answers.filter(
            criterion__section=section,
        )
    }

    criteria = list(
        section.criteria
        .prefetch_related("options")
        .all()
    )

    for criterion in criteria:
        options = list(
            criterion.options.all()
        )

        criterion.teacher_options = [
            option
            for option in options
            if option.side == ChecklistOption.Side.TEACHER
        ]

        criterion.student_options = [
            option
            for option in options
            if option.side == ChecklistOption.Side.STUDENT
        ]

        criterion.current_answer = answers.get(
            criterion.pk
        )

    return criteria


def get_progress(assessment):
    criteria = list(
        ChecklistCriterion.objects
        .filter(
            section__template=assessment.template,
        )
        .prefetch_related("options")
    )

    answers = {
        answer.criterion_id: answer
        for answer in assessment.answers.all()
    }

    completed = 0

    for criterion in criteria:
        options = list(
            criterion.options.all()
        )

        teacher_required = any(
            option.side == ChecklistOption.Side.TEACHER
            for option in options
        )

        student_required = any(
            option.side == ChecklistOption.Side.STUDENT
            for option in options
        )

        answer = answers.get(
            criterion.pk
        )

        if not answer:
            continue

        teacher_ok = (
            not teacher_required
            or answer.teacher_option_id is not None
        )

        student_ok = (
            not student_required
            or answer.student_option_id is not None
        )

        if teacher_ok and student_ok:
            completed += 1

    return completed, len(criteria)


def save_section_answers(
    request,
    assessment,
    criteria,
):
    """
    Сохраняет ответы текущего блока.

    Важно:
    если какое-либо поле отсутствует в POST,
    существующее значение НЕ затирается.
    """

    with transaction.atomic():

        for criterion in criteria:

            answer, _ = (
                AssessmentAnswer.objects
                .get_or_create(
                    assessment=assessment,
                    criterion=criterion,
                )
            )

            teacher_field = (
                f"teacher_{criterion.pk}"
            )

            student_field = (
                f"student_{criterion.pk}"
            )

            comment_field = (
                f"comment_{criterion.pk}"
            )

            # --------------------------
            # Ответ преподавателя
            # --------------------------

            if teacher_field in request.POST:

                teacher_value = request.POST.get(
                    teacher_field
                )

                valid_teacher_options = {
                    str(option.pk): option
                    for option
                    in criterion.teacher_options
                }

                teacher_option = (
                    valid_teacher_options.get(
                        teacher_value
                    )
                )

                if teacher_option is None:
                    return HttpResponseBadRequest(
                        "Некорректный вариант "
                        "оценки преподавателя."
                    )

                answer.teacher_option = (
                    teacher_option
                )

            # --------------------------
            # Ответ студента
            # --------------------------

            if student_field in request.POST:

                student_value = request.POST.get(
                    student_field
                )

                valid_student_options = {
                    str(option.pk): option
                    for option
                    in criterion.student_options
                }

                student_option = (
                    valid_student_options.get(
                        student_value
                    )
                )

                if student_option is None:
                    return HttpResponseBadRequest(
                        "Некорректный вариант "
                        "оценки студента."
                    )

                answer.student_option = (
                    student_option
                )

            # --------------------------
            # Комментарий
            # --------------------------

            if comment_field in request.POST:
                answer.comment = (
                    request.POST.get(
                        comment_field,
                        "",
                    ).strip()
                )

            answer.full_clean()
            answer.save()

        assessment.updated_by = request.user
        assessment.status = (
            Assessment.Status.DRAFT
        )
        assessment.completed_at = None

        assessment.save(
            update_fields=[
                "updated_by",
                "status",
                "completed_at",
                "updated_at",
            ]
        )

    return None


@login_required
def checklist_start(
    request,
    visit_id,
):
    visit = get_object_or_404(
        Visit,
        pk=visit_id,
    )

    if not can_edit_visit(
        request.user,
        visit,
    ):
        return HttpResponseBadRequest(
            "У вас нет прав на заполнение "
            "этого посещения."
        )

    template_code = (
        "online"
        if visit.format == Visit.Format.ONLINE
        else "oup"
    )

    template = get_object_or_404(
        ChecklistTemplate,
        code=template_code,
        is_active=True,
    )

    try:
        assessment = visit.assessment

    except Assessment.DoesNotExist:
        assessment = Assessment.objects.create(
            visit=visit,
            template=template,
            updated_by=request.user,
        )

    if assessment.template_id != template.id:
        messages.error(
            request,
            (
                "К этому посещению привязан чек-лист "
                "другого формата. Его необходимо "
                "сбросить перед началом нового оценивания."
            ),
        )

        return redirect(
            "visits:detail",
            pk=visit.pk,
        )

    first_section = (
        template.sections
        .order_by("order")
        .first()
    )

    if first_section is None:
        messages.error(
            request,
            "В шаблоне отсутствуют блоки.",
        )

        return redirect(
            "visits:detail",
            pk=visit.pk,
        )

    return redirect(
        "checklists:section",
        visit_id=visit.pk,
        section_order=first_section.order,
    )


@login_required
def assessment_result(
    request,
    visit_id,
):
    visit = get_object_or_404(
        Visit.objects.select_related(
            "teacher"
        ).prefetch_related(
            "auditors"
        ),
        pk=visit_id,
    )

    assessment = get_object_or_404(
        Assessment.objects.select_related(
            "template"
        ),
        visit=visit,
    )

    answers = {
        answer.criterion_id: answer
        for answer in assessment.answers.select_related(
            "teacher_option",
            "student_option",
        )
    }

    sections = list(
        assessment.template.sections
        .order_by("order")
        .prefetch_related(
            "criteria__options"
        )
    )

    for section in sections:
        section_score = 0
        section_max = 0

        criteria = list(
            section.criteria.all()
        )

        for criterion in criteria:
            answer = answers.get(
                criterion.pk
            )

            criterion.current_answer = answer

            score = 0

            if answer:
                if answer.teacher_option:
                    score += (
                        answer.teacher_option.score
                    )

                if answer.student_option:
                    score += (
                        answer.student_option.score
                    )

            criterion.answer_score = score
            criterion.max_possible_score = (
                criterion.max_score
            )

            section_score += score
            section_max += criterion.max_score

        section.result_score = section_score
        section.result_max = section_max
        section.result_criteria = criteria

    expected_template_code = (
        "online"
        if visit.format == Visit.Format.ONLINE
        else "oup"
    )

    template_mismatch = (
        assessment.template.code
        != expected_template_code
    )

    context = {
        "visit": visit,
        "assessment": assessment,
        "sections": sections,
        "template_mismatch": template_mismatch,
        "can_edit": (
            can_edit_visit(
                request.user,
                visit,
            )
            and not template_mismatch
        ),
    }

    return render(
        request,
        "checklists/result.html",
        context,
    )


@login_required
def checklist_section(
    request,
    visit_id,
    section_order,
):
    visit = get_object_or_404(
        Visit.objects.select_related(
            "teacher"
        ),
        pk=visit_id,
    )

    if not can_edit_visit(
        request.user,
        visit,
    ):
        return HttpResponseBadRequest(
            "У вас нет прав на заполнение "
            "этого посещения."
        )

    assessment = get_object_or_404(
        Assessment.objects.select_related(
            "template",
        ),
        visit=visit,
    )

    section = get_object_or_404(
        ChecklistSection,
        template=assessment.template,
        order=section_order,
    )

    criteria = prepare_section(
        section,
        assessment,
    )

    sections = list(
        assessment.template.sections
        .order_by("order")
    )

    section_orders = [
        item.order
        for item in sections
    ]

    current_index = (
        section_orders.index(
            section.order
        )
    )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        save_error = save_section_answers(
            request,
            assessment,
            criteria,
        )

        if save_error:
            return save_error

        action = request.POST.get(
            "action",
            "save",
        )

        # ------------------------------
        # Назад
        # ------------------------------

        if action == "previous":

            if current_index > 0:
                return redirect(
                    "checklists:section",
                    visit_id=visit.pk,
                    section_order=(
                        section_orders[
                            current_index - 1
                        ]
                    ),
                )

        # ------------------------------
        # Далее
        # ------------------------------

        if action == "next":

            if (
                current_index
                < len(section_orders) - 1
            ):
                return redirect(
                    "checklists:section",
                    visit_id=visit.pk,
                    section_order=(
                        section_orders[
                            current_index + 1
                        ]
                    ),
                )

        # ------------------------------
        # Завершить
        # ------------------------------

        if action == "finish":

            completed, total = (
                get_progress(
                    assessment
                )
            )

            if completed != total:

                messages.error(
                    request,
                    (
                        "Нельзя завершить "
                        "чек-лист: "
                        f"заполнено "
                        f"{completed} из "
                        f"{total} критериев."
                    ),
                )

                return redirect(
                    "checklists:section",
                    visit_id=visit.pk,
                    section_order=section.order,
                )

            assessment.status = (
                Assessment.Status.COMPLETED
            )

            assessment.completed_at = (
                timezone.now()
            )

            assessment.updated_by = (
                request.user
            )

            assessment.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "updated_by",
                    "updated_at",
                ]
            )

            visit.status = (
                Visit.Status.COMPLETED
            )

            visit.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            return redirect(
                "visits:detail",
                pk=visit.pk,
            )

        # ====================================================
        # ВАЖНО:
        # обычное "Сохранить" всегда делает новый GET.
        #
        # Благодаря этому:
        # - баллы не пропадают;
        # - radio остаются отмечены;
        # - прогресс перечитывается из БД;
        # - повторный POST по F5 невозможен.
        # ====================================================

        return redirect(
            "checklists:section",
            visit_id=visit.pk,
            section_order=section.order,
        )

    # ========================================================
    # GET
    # ========================================================

    completed, total = (
        get_progress(
            assessment
        )
    )

    progress_percent = (
        round(
            completed / total * 100
        )
        if total
        else 0
    )

    previous_order = (
        section_orders[
            current_index - 1
        ]
        if current_index > 0
        else None
    )

    next_order = (
        section_orders[
            current_index + 1
        ]
        if (
            current_index
            < len(section_orders) - 1
        )
        else None
    )

    context = {
        "visit": visit,
        "assessment": assessment,
        "section": section,
        "criteria": criteria,

        "section_number": (
            current_index + 1
        ),

        "section_count": len(
            sections
        ),

        "previous_order": (
            previous_order
        ),

        "next_order": next_order,

        "completed": completed,
        "total": total,

        "progress_percent": (
            progress_percent
        ),
    }

    return render(
        request,
        "checklists/section.html",
        context,
    )
