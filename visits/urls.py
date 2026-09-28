from django.urls import path

from .views import (
    visit_cancel,
    visit_create,
    visit_detail,
    visit_edit,
    visit_list,
)


app_name = "visits"


urlpatterns = [

    path(
        "",
        visit_list,
        name="list",
    ),

    path(
        "new/",
        visit_create,
        name="create",
    ),

    path(
        "<int:pk>/",
        visit_detail,
        name="detail",
    ),

    path(
        "<int:pk>/edit/",
        visit_edit,
        name="edit",
    ),

    path(
        "<int:pk>/cancel/",
        visit_cancel,
        name="cancel",
    ),

]
