from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from datetime import timedelta

class TeacherManager(BaseUserManager):
    """
    Custom manager for the Teacher model.
    """

    def create_user(self, phone_number, password= None,**extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required.")

        phone_number = self.normalize_phone_number(phone_number)

        user = self.model(
            phone_number=phone_number,
            **extra_fields
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number,**extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
      

        return self.create_user(
            phone_number=phone_number,
            **extra_fields
        )

    @staticmethod
    def normalize_phone_number(phone_number):
        """
        Normalize Iranian phone numbers.

        Accepted examples:
            09123456789
            +989123456789
        Stored format:
            09123456789
        """

        phone_number = phone_number.strip()

        if phone_number.startswith("+98"):
            phone_number = "0" + phone_number[3:]

        return phone_number


class Teacher(AbstractBaseUser, PermissionsMixin):

    # ------------------------------------------------------------------
    # Choices
    # ------------------------------------------------------------------

    GENDER_CHOICES = [
        ("man", "مرد"),
        ("woman", "زن"),
    ]

    POSITION_CHOICES = [
        ("teacher", "معلم"),
        ("Instructor", "مربی"),
        ("Amin Program Educator", "مربی طرح امین"),
        ("Independent Preacher", "مبلغ آزاد"),
    ]

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    phone_validator = RegexValidator(
        regex=r"^09\d{9}$",
        message="Phone number must contain exactly 11 digits and start with 09."
    )

    national_id_validator = RegexValidator(
        regex=r"^\d{10}$",
        message="National ID must contain exactly 10 digits."
    )

    # ------------------------------------------------------------------
    # Personal Information
    # ------------------------------------------------------------------

    first_name = models.CharField(
        max_length=100,
        verbose_name="نام"
    )

    last_name = models.CharField(
        max_length=100,
        verbose_name="نام خانوادگی"
    )

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------

    province = models.CharField(
        max_length=100,
        verbose_name="استان"
    )

    city = models.CharField(
        max_length=100,
        verbose_name="شهرستان"
    )

    village = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="روستا"
    )

    # ------------------------------------------------------------------
    # School Information
    # ------------------------------------------------------------------

    school = models.CharField(
        max_length=200,
        verbose_name="مدرسه"
    )

    grade = models.ManyToManyField(
        "Grade",
        blank=True,
        related_name="teachers"
    )

    position = models.CharField(
        max_length=30,
        choices=POSITION_CHOICES,
        verbose_name="سمت"
    )

    gender = models.CharField(
        max_length=30,
        choices=GENDER_CHOICES,
        verbose_name="جنسیت",
        blank=True,
    )
    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    phone_number = models.CharField(
        max_length=11,
        unique=True,
        validators=[phone_validator],
        verbose_name="شماره تماس"
    )

    # ------------------------------------------------------------------
    # National ID
    # ------------------------------------------------------------------

    national_id = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="کد ملی",
        blank= True,
        null=True
    )

    # ------------------------------------------------------------------
    # Django permissions / status
    # ------------------------------------------------------------------

    is_active = models.BooleanField(
        default=True
    )

    is_staff = models.BooleanField(
        default=False
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # ------------------------------------------------------------------
    # Django User configuration
    # ------------------------------------------------------------------

    USERNAME_FIELD = "phone_number"

    REQUIRED_FIELDS = []

    objects = TeacherManager()

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.phone_number}"


class OTPVerification(models.Model):

    phone_number = models.CharField(
        max_length=11,
        validators=[
            RegexValidator(
                regex=r"^09\d{9}$",
                message="Phone number must contain exactly 11 digits and start with 09."
            )
        ]
    )

    code = models.CharField(
        max_length=4
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_verified = models.BooleanField(
        default=False
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        # Never expose the OTP code through admin/log representations.
        return f"OTP for {self.phone_number}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @classmethod
    def create_otp(cls, phone_number, code, expire_minutes=None):
        if expire_minutes is None:
            expire_minutes = getattr(settings, "OTP_EXPIRE_MINUTES", 3)

        return cls.objects.create(
            phone_number=phone_number,
            code=code,
            expires_at=timezone.now() + timedelta(
                minutes=expire_minutes
            )
        )
        
class Grade(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True
    )

    value = models.CharField(
        max_length=20,
        unique=True
    )
