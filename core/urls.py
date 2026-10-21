from django.urls import path

from .views import (
    home,
    monitoring,
    teacher_monitoring,
    diagnostics,
)


app_name = "core"


urlpatterns = [
    path("diagnostics/", diagnostics, name="diagnostics"),

    path(
        "",
        home,
        name="home",
    ),

    path(
        "monitoring/",
        monitoring,
        name="monitoring",
    ),

    path(
        "monitoring/teacher/<int:teacher_id>/",
        teacher_monitoring,
        name="teacher_monitoring",
    ),

]
