from rest_framework import serializers

from accounts.models import Teacher
from reports.models import Point, Report, ReportImage, ReportVideo, Tag
from survey.models import Survey, Question, Option, Submission, Answer
from tickets.models import Ticket

def get_teacher_name(teacher):
    if not teacher:
        return None

    return f"{teacher.first_name} {teacher.last_name}".strip()

class AdminTeacherSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    report_count = serializers.SerializerMethodField()
    point_total = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "national_id",
            "province",
            "city",
            "village",
            "school",
            "grade",
            "position",
            "gender",
            "report_count",
            "point_total",
        ]

    def get_full_name(self, obj) -> str:
        return get_teacher_name(obj)

    def get_grade(self, obj) -> list:
        return list(
            obj.grade.values_list("name", flat=True)
        )

    def get_report_count(self, obj) -> int:
        return obj.reports.count()

    def get_point_total(self, obj) -> int:
        return sum(
            point.score
            for point in obj.points.all()
        )


class AdminTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
        "id",
        "name",
        "created_at",
        ]

class AdminReportSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()

    teacher_phone = serializers.CharField(
        source="teacher.phone_number",
        read_only=True,
        allow_null=True,
    )

    teacher_province = serializers.CharField(
        source="teacher.province",
        read_only=True,
        allow_null=True,
    )

    teacher_city = serializers.CharField(
        source="teacher.city",
        read_only=True,
        allow_null=True,
    )

    teacher_school = serializers.CharField(
        source="teacher.school",
        read_only=True,
        allow_null=True,
    )

    tags = AdminTagSerializer(
        many=True,
        read_only=True,
    )

    images = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()

    images_count = serializers.SerializerMethodField()
    videos_count = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "teacher",
            "teacher_name",
            "teacher_phone",
            "teacher_province",
            "teacher_city",
            "teacher_school",
            "text",
            "tags",
            "images",
            "videos",
            "images_count",
            "videos_count",
            "created_at",
            "updated_at",
        ]

    def get_teacher_name(self, obj) -> str | None:
        return get_teacher_name(obj.teacher)

    def get_images(self, obj) -> list:
        request = self.context.get("request")
        result = []

        for image in obj.images.all():
            url = image.image.url if image.image else None

            if request and url:
                url = request.build_absolute_uri(url)

            result.append({
                "id": image.id,
                "url": url,
                "created_at": image.created_at,
            })

        return result

    def get_videos(self, obj) -> list:
        request = self.context.get("request")
        result = []

        for video in obj.videos.all():
            url = video.video.url if video.video else None

            if request and url:
                url = request.build_absolute_uri(url)

            result.append({
                "id": video.id,
                "url": url,
                "created_at": video.created_at,
            })

        return result

    def get_images_count(self, obj) -> int:
        return obj.images.count()

    def get_videos_count(self, obj) -> int:
        return obj.videos.count()

class AdminReportImageSerializer(serializers.ModelSerializer):
    media_type = serializers.SerializerMethodField()

    teacher_id = serializers.IntegerField(
        source="report.teacher.id",
        read_only=True,
        allow_null=True,
    )

    teacher_name = serializers.SerializerMethodField()

    teacher_phone = serializers.CharField(
        source="report.teacher.phone_number",
        read_only=True,
        allow_null=True,
    )

    province = serializers.CharField(
        source="report.teacher.province",
        read_only=True,
        allow_null=True,
    )

    city = serializers.CharField(
        source="report.teacher.city",
        read_only=True,
        allow_null=True,
    )

    school = serializers.CharField(
        source="report.teacher.school",
        read_only=True,
        allow_null=True,
    )

    tags = AdminTagSerializer(
        source="report.tags",
        many=True,
        read_only=True,
    )

    report_text = serializers.CharField(
        source="report.text",
        read_only=True,
    )

    report_created_at = serializers.DateTimeField(
        source="report.created_at",
        read_only=True,
    )

    class Meta:
        model = ReportImage
        fields = [
            "id",
            "report",
            "image",
            "media_type",
            "teacher_id",
            "teacher_name",
            "teacher_phone",
            "province",
            "city",
            "school",
            "tags",
            "report_text",
            "report_created_at",
            "created_at",
        ]

    def get_media_type(self, obj) -> str:
        return "image"

    def get_teacher_name(self, obj) -> str | None:
        return get_teacher_name(
            getattr(obj.report, "teacher", None)
        )

class AdminReportVideoSerializer(serializers.ModelSerializer):
    media_type = serializers.SerializerMethodField()

    teacher_id = serializers.IntegerField(
        source="report.teacher.id",
        read_only=True,
        allow_null=True,
    )

    teacher_name = serializers.SerializerMethodField()

    teacher_phone = serializers.CharField(
        source="report.teacher.phone_number",
        read_only=True,
        allow_null=True,
    )

    province = serializers.CharField(
        source="report.teacher.province",
        read_only=True,
        allow_null=True,
    )

    city = serializers.CharField(
        source="report.teacher.city",
        read_only=True,
        allow_null=True,
    )

    school = serializers.CharField(
        source="report.teacher.school",
        read_only=True,
        allow_null=True,
    )

    tags = AdminTagSerializer(
        source="report.tags",
        many=True,
        read_only=True,
    )

    report_text = serializers.CharField(
        source="report.text",
        read_only=True,
    )

    report_created_at = serializers.DateTimeField(
        source="report.created_at",
        read_only=True,
    )

    class Meta:
        model = ReportVideo
        fields = [
            "id",
            "report",
            "video",
            "media_type",
            "teacher_id",
            "teacher_name",
            "teacher_phone",
            "province",
            "city",
            "school",
            "tags",
            "report_text",
            "report_created_at",
            "created_at",
        ]

    def get_media_type(self, obj) -> str:
        return "video"

    def get_teacher_name(self, obj) -> str | None:
        return get_teacher_name(
            getattr(obj.report, "teacher", None)
        )

class AdminPointSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Point
        fields = [
            "id",
            "teacher",
            "teacher_name",
            "score",
            "reason",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "teacher_name",
            "created_at",
        ]

    def get_teacher_name(self, obj) -> str | None:
        return get_teacher_name(obj.teacher)

class AdminOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = [
        "id",
        "question",
        "text",
        "order",
        ]

class AdminQuestionSerializer(serializers.ModelSerializer):
    options = AdminOptionSerializer(
    many=True,
    read_only=True,
    )

    class Meta:
        model = Question
        fields = [
            "id",
            "survey",
            "text",
            "question_type",
            "is_required",
            "order",
            "options",
        ]

class AdminSurveySerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = Survey
        fields = [
            "id",
            "title",
            "description",
            "is_active",
            "question_count",
            "submission_count",
            "created_at",
        ]

    def get_question_count(self, obj) -> int:
        return getattr(
            obj,
            "annotated_question_count",
            obj.questions.count(),
        )

    def get_submission_count(self, obj) -> int:
        return getattr(
            obj,
            "annotated_submission_count",
            obj.submissions.count(),
        )

class AdminSubmissionSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    user_phone = serializers.CharField(
        source="user.phone_number",
        read_only=True,
        default=None,
    )

    survey_title = serializers.CharField(
        source="survey.title",
        read_only=True,
    )

    class Meta:
        model = Submission
        fields = [
            "id",
            "survey",
            "survey_title",
            "user",
            "user_name",
            "user_phone",
            "created_at",
        ]

    def get_user_name(self, obj) -> str | None:
        return get_teacher_name(obj.user)

class AdminAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(
    source="question.text",
    read_only=True,
    )

    selected_options = AdminOptionSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Answer
        fields = [
            "id",
            "submission",
            "question",
            "question_text",
            "text_answer",
            "selected_options",
        ]
        
        
class AdminReportWithMediaSerializer(serializers.ModelSerializer):
    images = AdminReportImageSerializer(many=True, read_only=True)
    videos = AdminReportVideoSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = ["id", "teacher", "text", "images", "videos", "created_at"]



class AdminTicketSerializer(serializers.ModelSerializer):

      class Meta:
            model = Ticket
            fields = [
                  "id",
                  "title",
                  "content",
                  "first_name",
                  "last_name",
                  "phone_number",
                  "answer",
                  "is_answered",
                  "created_at",
                  "updated_at",
            ]

            read_only_fields = [
                  "id",
                  "title",
                  "content",
                  "first_name",
                  "last_name",
                  "phone_number",
                  "is_answered",
                  "created_at",
                  "updated_at",
            ]
