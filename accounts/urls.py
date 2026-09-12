from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.BlogLoginView.as_view(), name="login"),
    path("logout/", views.BlogLogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("settings/", views.profile_edit, name="profile_edit"),
    path("settings/password/", views.BlogPasswordChangeView.as_view(), name="password_change"),
]
