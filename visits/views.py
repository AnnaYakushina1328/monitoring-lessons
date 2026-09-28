from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import VisitForm
from .models import Visit


@login_required
def visit_list(request):
    visits = (
        Visit.objects
        .select_related("teacher")
        .prefetch_related("auditors")
    )

    return render(
        request,
        "visits/list.html",
        {
            "visits": visits,
        },
    )


@login_required
def visit_detail(request, pk):
    visit = get_object_or_404(
        Visit.objects
        .select_related("teacher")
        .prefetch_related("auditors"),
        pk=pk,
    )

    try:
        assessment = visit.assessment
    except Exception:
        assessment = None

    expected_template_code = (
        "online"
        if visit.format == Visit.Format.ONLINE
        else "oup"
    )

    assessment_mismatch = (
        assessment is not None
        and assessment.template.code
        != expected_template_code
    )

    checklist_label = (
        "Онлайн-чек-лист"
        if visit.format == Visit.Format.ONLINE
        else "Чек-лист ОУП"
    )

    return render(
        request,
        "visits/detail.html",
        {
            "visit": visit,
            "assessment": assessment,
            "assessment_mismatch": assessment_mismatch,
            "checklist_label": checklist_label,
        },
    )


@login_required
def visit_create(request):
    if request.method == "POST":
        form = VisitForm(request.POST)

        if form.is_valid():
            visit = form.save(commit=False)
            visit.created_by = request.user
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
