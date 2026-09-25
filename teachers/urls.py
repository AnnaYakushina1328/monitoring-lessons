from django.urls import path

from .views import teacher_list


app_name = "teachers"

urlpatterns = [
    path("", teacher_list, name="list"),
]
