from django.db import migrations


GRADES = [
    ("first", "پایه اول"),
    ("second", "پایه دوم"),
    ("third", "پایه سوم"),
    ("fourth", "پایه چهارم"),
    ("fifth", "پایه پنجم"),
    ("sixth", "پایه ششم"),
]


def seed_grades(apps, schema_editor):
    Grade = apps.get_model("accounts", "Grade")

    for value, name in GRADES:
        Grade.objects.get_or_create(
            value=value,
            defaults={"name": name},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_alter_teacher_national_id"),
    ]

    operations = [
        migrations.RunPython(seed_grades, migrations.RunPython.noop),
    ]
