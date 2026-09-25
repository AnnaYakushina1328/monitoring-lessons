from django.urls import path

from .views import (
    checklist_section,
    checklist_start,
)


app_name = "checklists"


urlpatterns = [
    path(
        "visit/<int:visit_id>/start/",
        checklist_start,
        name="start",
    ),

    path(
        "visit/<int:visit_id>/section/<int:section_order>/",
        checklist_section,
        name="section",
    ),
]
