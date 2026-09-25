from django.urls import path

from .views import visit_create, visit_list


app_name = "visits"


urlpatterns = [
    path("", visit_list, name="list"),
    path("new/", visit_create, name="create"),
]
