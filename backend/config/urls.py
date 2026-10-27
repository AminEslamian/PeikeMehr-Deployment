from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from rest_framework.permissions import AllowAny, IsAdminUser

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from .health import health
from .view import (
    home,
    login_page,
    login_verify_page,
    register_page,
    register_verify_page,
    dashboard_page,
    main_page,
    survey_page,
    contact_page,
)




docs_permissions = (
    [AllowAny]
    if getattr(settings, "API_DOCS_PUBLIC", False)
    else [IsAdminUser]
)

urlpatterns = [
    # ─── Health check ───
    path("health/", health, name="health"),

    # ─── Admin ───
    path("admin/", admin.site.urls),
    path("admin-panel/", include("adminpanel.urls")),


    # =========================================================
    # Public Pages
    # =========================================================

    path(
        "",
        home,
        name="home",
    ),

    path(
        "contact/",
        contact_page,
        name="contact",
    ),
    path(
        "login/",
        login_page,
        name="login",
    ),

    path(
        "login/verify/",
        login_verify_page,
        name="login-verify",
    ),

    path(
        "register/",
        register_page,
        name="register",
    ),

    path(
        "register/verify/",
        register_verify_page,
        name="register-verify",
    ),

    path(
        "main/",
        main_page,
        name="main",
    ),

    path(
        "dashboard/",
        dashboard_page,
        name="dashboard",
    ),

    path(
        "survey/",
        survey_page,
        name="survey",
    ),

    # ─── API ───
    path("api/auth/", include("accounts.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/surveys/", include("survey.urls")),
    path("api/blogs/", include("blogs.urls")),
    path("api/tickets/", include("tickets.urls")),

    # ─── API Docs ───
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=docs_permissions),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            permission_classes=docs_permissions,
        ),
        name="swagger-ui",
    ),
]


# ─── Media files (dev only) ───
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )