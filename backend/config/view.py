
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from reports.models import Point
from accounts.models import Teacher
from reports.models import Report, Tag
from survey.models import (
    Option,
    Question,
    QuestionType,
    Survey,
)


# =========================
# Public Pages
# =========================

from django.shortcuts import redirect
from rest_framework_simplejwt.authentication import JWTAuthentication


def home(request):
    return render(request, "home.html")


def login_page(request):
    return render(request, "login.html")


def login_verify_page(request):
    return render(request, "login_verify.html")


def register_page(request):
    return render(request, "register.html")


def register_verify_page(request):
    return render(request, "register_verify.html")


def dashboard_page(request):
    return render(request, "dashboard.html")


def main_page(request):
    return render(request, "main.html")


def survey_page(request):
    return render(request, "survey.html")

def contact_page(request):
    return render(request, "contact.html")