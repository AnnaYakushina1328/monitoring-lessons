from django import forms

from accounts.models import User

from .models import Visit


class VisitForm(forms.ModelForm):

    class Meta:
        model = Visit

        fields = [
            "teacher",
            "date",
            "lesson_number",
            "subject",
            "group",
            "room",
            "topic",
            "purpose",
            "format",
            "auditors",
            "is_open_lesson",
            "notes",
        ]

        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),

            "topic": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),

            "purpose": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),

            "auditors": (
                forms.CheckboxSelectMultiple()
            ),
        }


    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "auditors"
        ].queryset = (
            User.objects
            .filter(
                role=User.Role.EXPERT,
                is_active=True,
            )
            .order_by(
                "last_name",
                "first_name",
                "username",
            )
        )
