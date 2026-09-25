from django.urls import path

from .views import (
    visit_create,
    visit_detail,
    visit_list,
)


app_name = "visits"


urlpatterns = [
    path("", visit_list, name="list"),
    path("new/", visit_create, name="create"),
    path("<int:pk>/", visit_detail, name="detail"),
]
