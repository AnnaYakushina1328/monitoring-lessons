from django.db.models import Q
from django.shortcuts import render

from .models import Teacher


def teacher_list(request):
    query = request.GET.get("q", "").strip()

    teachers = Teacher.objects.filter(
        is_active=True
    )

    if query:
        teachers = teachers.filter(
            Q(full_name__icontains=query)
            | Q(position__icontains=query)
        )

    context = {
        "teachers": teachers,
        "query": query,
        "count": teachers.count(),
    }

    return render(
        request,
        "teachers/list.html",
        context,
    )
