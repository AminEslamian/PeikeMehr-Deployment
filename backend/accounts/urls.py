from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    SendOTPView,
    VerifyOTPView,
    RegisterSendOTPView,
    RegisterVerifyOTPView,
    ProfileViewSet,
)


urlpatterns = [
    path("login/send-otp/", SendOTPView.as_view(), name="login-send-otp"),
    path("login/verify-otp/", VerifyOTPView.as_view(), name="login-verify-otp"),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path(
        "register/send-otp/",
        RegisterSendOTPView.as_view(),
        name="register-send-otp",
    ),
    path(
        "register/verify-otp/",
        RegisterVerifyOTPView.as_view(),
        name="register-verify-otp",
    ),
    path(
        "profile/",
        ProfileViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
        }),
        name="profile",)
]