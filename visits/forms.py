from django import forms

from .models import Visit


class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit

        fields = (
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
        )

        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
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

            "auditors": forms.CheckboxSelectMultiple(),
        }
