from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Teacher
from survey.models import (
    Answer,
    Option,
    Question,
    QuestionType,
    Submission,
    Survey,
)


def make_teacher(**kwargs):
    defaults = {
        "phone_number": "09123456789",
        "first_name": "Audit",
        "last_name": "Teacher",
        "province": "Qom",
        "city": "Qom",
        "school": "Audit School",
        "position": "teacher",
        "gender": "man",
        "national_id": "1234567890",
    }
    defaults.update(kwargs)
    return Teacher.objects.create(**defaults)


class SurveyAPITests(APITestCase):
    def setUp(self):
        self.teacher = make_teacher()
        self.other = make_teacher(
            phone_number="09120000000",
            national_id="0000000001",
        )
        self.survey = Survey.objects.create(title="Audit survey")
        self.text_question = Question.objects.create(
            survey=self.survey,
            text="Describe your class",
            question_type=QuestionType.TEXT,
            is_required=True,
            order=1,
        )
        self.single_question = Question.objects.create(
            survey=self.survey,
            text="Pick one",
            question_type=QuestionType.SINGLE_CHOICE,
            is_required=True,
            order=2,
        )
        self.single_a = Option.objects.create(
            question=self.single_question, text="A", order=1
        )
        self.single_b = Option.objects.create(
            question=self.single_question, text="B", order=2
        )
        self.other_question = Question.objects.create(
            survey=self.survey,
            text="Unrelated",
            question_type=QuestionType.SINGLE_CHOICE,
            is_required=False,
            order=3,
        )
        self.other_option = Option.objects.create(
            question=self.other_question, text="X", order=1
        )
        self.list_url = "/api/surveys/"

    def _valid_answers(self):
        return [
            {"question_id": self.text_question.id, "text_answer": "A good class"},
            {
                "question_id": self.single_question.id,
                "selected_options": [self.single_a.id],
            },
        ]

    def test_unauthenticated_list_rejected(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_active_surveys(self):
        inactive = Survey.objects.create(title="Inactive", is_active=False)
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data]
        self.assertIn(self.survey.id, ids)
        self.assertNotIn(inactive.id, ids)

    def test_inactive_survey_detail_returns_404(self):
        inactive = Survey.objects.create(title="Inactive", is_active=False)
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(f"{self.list_url}{inactive.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_required_text_answer_rejected(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            f"{self.list_url}{self.survey.id}/submit/",
            {"answers": [self._valid_answers()[1]]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_text_answer_for_choice_question_rejected(self):
        self.client.force_authenticate(user=self.teacher)
        answers = self._valid_answers()
        answers[1] = {
            "question_id": self.single_question.id,
            "text_answer": "not allowed",
            "selected_options": [self.single_a.id],
        }
        response = self.client.post(
            f"{self.list_url}{self.survey.id}/submit/",
            {"answers": answers},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_single_choice_with_two_options_rejected(self):
        self.client.force_authenticate(user=self.teacher)
        answers = self._valid_answers()
        answers[1]["selected_options"] = [self.single_a.id, self.single_b.id]
        response = self.client.post(
            f"{self.list_url}{self.survey.id}/submit/",
            {"answers": answers},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_option_from_another_question_rejected(self):
        self.client.force_authenticate(user=self.teacher)
        answers = self._valid_answers()
        answers[1]["selected_options"] = [self.other_option.id]
        response = self.client.post(
            f"{self.list_url}{self.survey.id}/submit/",
            {"answers": answers},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_question_from_another_survey_rejected(self):
        other_survey = Survey.objects.create(title="Other")
        foreign = Question.objects.create(
            survey=other_survey,
            text="Foreign",
            question_type=QuestionType.TEXT,
            is_required=False,
        )
        self.client.force_authenticate(user=self.teacher)
        answers = self._valid_answers()
        answers.append({"question_id": foreign.id, "text_answer": "x"})
        response = self.client.post(
            f"{self.list_url}{self.survey.id}/submit/",
            {"answers": answers},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_submission_creates_records(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            f"{self.list_url}{self.survey.id}/submit/",
            {"answers": self._valid_answers()},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Submission.objects.filter(user=self.teacher).count(), 1)
        self.assertEqual(Answer.objects.count(), 2)

    def test_resubmission_updates_without_duplicate(self):
        self.client.force_authenticate(user=self.teacher)
        self.client.post(
            f"{self.list_url}{self.survey.id}/submit/",
            {"answers": self._valid_answers()},
            format="json",
        )
        answers = self._valid_answers()
        answers[0]["text_answer"] = "Updated text"
        response = self.client.post(
            f"{self.list_url}{self.survey.id}/submit/",
            {"answers": answers},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Submission.objects.filter(user=self.teacher).count(), 1)
        answer = Answer.objects.get(
            submission__user=self.teacher,
            question=self.text_question,
        )
        self.assertEqual(answer.text_answer, "Updated text")

    def test_previous_answers_are_scoped_to_user(self):
        self.client.force_authenticate(user=self.teacher)
        self.client.post(
            f"{self.list_url}{self.survey.id}/submit/",
            {"answers": self._valid_answers()},
            format="json",
        )

        self.client.force_authenticate(user=self.other)
        response = self.client.get(f"{self.list_url}{self.survey.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["has_submitted"])
        self.assertEqual(response.data["previous_answers"], [])
