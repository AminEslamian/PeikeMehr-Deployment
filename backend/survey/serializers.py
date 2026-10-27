from django.db import transaction
from rest_framework import serializers

from .models import Answer, Option, Question, QuestionType, Submission, Survey


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "text", "order"]

class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "question_type",
            "is_required",
            "order",
            "options",
        ]

        
class Meta:
    model = Question
    fields = [
        "id",
        "text",
        "question_type",
        "is_required",
        "order",
        "options",
    ]
        

class ExistingAnswerSerializer(serializers.ModelSerializer):
    selected_options = OptionSerializer(many=True, read_only=True)

            
    class Meta:
        model = Answer
        fields = [
            "id",
            "question",
            "text_answer",
            "selected_options",
        ]
        

class SurveyDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    has_submitted = serializers.SerializerMethodField()
    previous_answers = serializers.SerializerMethodField()

    class Meta:
        model = Survey
        fields = [
            "id",
            "title",
            "description",
            "questions",
            "has_submitted",
            "previous_answers",
        ]

    def get_user_submission(self, obj):
        request = self.context.get("request")

        if not request:
            return None

        user = request.user

        if not user or not user.is_authenticated:
            return None

        return (
            obj.submissions
            .filter(user=user)
            .prefetch_related("answers__selected_options")
            .first()
        )

    def get_has_submitted(self, obj) -> bool:
        return self.get_user_submission(obj) is not None

    def get_previous_answers(self, obj) -> list:
        submission = self.get_user_submission(obj)

        if not submission:
            return []

        return ExistingAnswerSerializer(
            submission.answers.all(),
            many=True,
        ).data


class SurveyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ["id", "title", "description", "created_at"]


class AnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()

    text_answer = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    selected_options = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[],
    )


class SubmissionCreateSerializer(serializers.Serializer):
    answers = AnswerSubmitSerializer(many=True)

    def validate(self, attrs):
        survey = self.context["survey"]
        user = self.context["request"].user
        answers_data = attrs.get("answers", [])

        survey_questions = {
            q.id: q
            for q in survey.questions.all()
        }

        submitted_q_ids = {
            answer["question_id"]
            for answer in answers_data
        }

        # ۱. بررسی سوالات الزامی
        for q_id, question in survey_questions.items():
            if question.is_required and q_id not in submitted_q_ids:
                raise serializers.ValidationError(
                    f"پاسخ به سوال '{question.text}' الزامی است."
                )

        # ۲. بررسی پاسخ‌های ارسال‌شده
        for item in answers_data:
            q_id = item["question_id"]

            if q_id not in survey_questions:
                raise serializers.ValidationError(
                    f"سوال با شناسه {q_id} متعلق به این نظرسنجی نیست."
                )

            question = survey_questions[q_id]

            text_ans = item.get("text_answer", "").strip()
            opt_ids = item.get("selected_options", [])

            # سوال تشریحی
            if question.question_type == QuestionType.TEXT:

                if question.is_required and not text_ans:
                    raise serializers.ValidationError(
                        f"پاسخ تشریحی برای سوال '{question.text}' نمی‌تواند خالی باشد."
                    )

                if opt_ids:
                    raise serializers.ValidationError(
                        f"برای سوال تشریحی '{question.text}' نمی‌توان گزینه انتخاب کرد."
                    )

            # سوال تک‌گزینه‌ای
            elif question.question_type == QuestionType.SINGLE_CHOICE:

                if text_ans:
                    raise serializers.ValidationError(
                        f"برای سوال '{question.text}' نباید پاسخ متنی ارسال شود."
                    )

                if len(opt_ids) > 1:
                    raise serializers.ValidationError(
                        f"برای سوال '{question.text}' تنها می‌توانید یک گزینه انتخاب کنید."
                    )

                if question.is_required and len(opt_ids) != 1:
                    raise serializers.ValidationError(
                        f"انتخاب یک گزینه برای سوال '{question.text}' الزامی است."
                    )

            # سوال چندگزینه‌ای
            elif question.question_type == QuestionType.MULTIPLE_CHOICE:

                if text_ans:
                    raise serializers.ValidationError(
                        f"برای سوال '{question.text}' نباید پاسخ متنی ارسال شود."
                    )

                if question.is_required and not opt_ids:
                    raise serializers.ValidationError(
                        f"حداقل یک گزینه برای سوال '{question.text}' باید انتخاب شود."
                    )

            # ۳. بررسی تعلق گزینه‌ها به سؤال
            if opt_ids:
                valid_opt_ids = set(
                    question.options.values_list(
                        "id",
                        flat=True,
                    )
                )

                for option_id in opt_ids:
                    if option_id not in valid_opt_ids:
                        raise serializers.ValidationError(
                            f"گزینه انتخاب‌شده با شناسه {option_id} "
                            f"متعلق به سوال '{question.text}' نیست."
                        )

        return attrs

    @transaction.atomic
    def save(self):
        survey = self.context["survey"]
        user = self.context["request"].user

        submission = (
            Submission.objects
            .filter(
                survey=survey,
                user=user,
            )
            .first()
        )

        if submission is None:
            submission = Submission.objects.create(
                survey=survey,
                user=user,
            )

        existing_answers = {
            answer.question_id: answer
            for answer in submission.answers.all()
        }

        submitted_question_ids = set()

        for item in self.validated_data["answers"]:
            q_id = item["question_id"]

            text_ans = item.get("text_answer", "").strip()
            opt_ids = item.get("selected_options", [])

            submitted_question_ids.add(q_id)

            answer = existing_answers.get(q_id)

            if answer is None:
                answer = Answer.objects.create(
                    submission=submission,
                    question_id=q_id,
                    text_answer=text_ans if text_ans else None,
                )
            else:
                answer.text_answer = (
                    text_ans
                    if text_ans
                    else None
                )

                answer.save()

            answer.selected_options.set(opt_ids)

        # پاسخ‌هایی که قبلاً وجود داشته‌اند ولی دیگر در فرم
        # ارسال نشده‌اند، حذف می‌شوند.
        for q_id, answer in existing_answers.items():
            if q_id not in submitted_question_ids:
                answer.delete()

        return submission
