from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path


urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),

    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "teachers/",
        include("teachers.urls"),
    ),

    path(
        "visits/",
        include("visits.urls"),
    ),

    path(
        "checklists/",
        include("checklists.urls"),
    ),

    path(
        "",
        include("core.urls"),
    ),
]
