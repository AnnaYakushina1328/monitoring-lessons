from django.urls import path

from .views import (
    assessment_result,
    acknowledge_result,
    checklist_section,
    checklist_start,
)


app_name = "checklists"


urlpatterns = [
    path(
        "visit/<int:visit_id>/acknowledge/",
        acknowledge_result,
        name="acknowledge",
    ),

    path(
        "visit/<int:visit_id>/start/",
        checklist_start,
        name="start",
    ),

    path(
        "visit/<int:visit_id>/result/",
        assessment_result,
        name="result",
    ),

    path(
        "visit/<int:visit_id>/section/<int:section_order>/",
        checklist_section,
        name="section",
    ),
]
