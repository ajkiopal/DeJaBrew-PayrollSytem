import re
import secrets
import string
from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password

from .models import Employee


def generate_temp_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            len(pwd) >= 8
            and any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
        ):
            return pwd


def validate_contact_number(value: str):
    raw = (value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{3}-\d{4}", raw):
        raise ValidationError("Invalid Format! (e.g. 09XX-XXX-XXXX).")


class BaseEmployeeForm(forms.ModelForm):
    def apply_ui(self):
        self.fields["name"].widget.attrs.update({"class": "inp", "placeholder": "Name"})
        self.fields["address"].widget.attrs.update({"class": "inp", "placeholder": "Address"})
        self.fields["job_title"].widget.attrs.update({"class": "inp", "placeholder": "Job Title"})
        self.fields["salary_rate"].widget.attrs.update({"class": "inp", "placeholder": "Salary (rate per hour)"})
        self.fields["contact_number"].widget.attrs.update(
            {"class": "inp", "placeholder": "Contact Number (####-###-####)"}
        )
        self.fields["role"].widget.attrs.update({"class": "sel"})
        self.fields["date_hired"].widget = forms.DateInput(
            attrs={
                "type": "date",
                "class": "inp",
                "max": date.today().isoformat(),
            }
        )
        self.fields["date_hired"].required = True

    def clean_contact_number(self):
        value = self.cleaned_data.get("contact_number", "")
        validate_contact_number(value)
        return value

    def clean_salary_rate(self):
        rate = self.cleaned_data.get("salary_rate")
        if rate is None or rate <= 0:
            raise ValidationError("Salary rate must be greater than 0.")
        return rate

    def clean_date_hired(self):
        d = self.cleaned_data.get("date_hired")
        if d is None:
            raise ValidationError("Date hired is required.")
        if d > date.today():
            raise ValidationError("Date hired must be today or earlier.")
        return d


class EmployeeCreateForm(BaseEmployeeForm):
    class Meta:
        model = Employee
        fields = [
            "name",
            "address",
            "job_title",
            "salary_rate",
            "contact_number",
            "date_hired",
            "role",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_ui()

    def save(self, commit=True):
        employee = super().save(commit=False)

        temp_password = generate_temp_password()
        employee.password_hash = make_password(temp_password)
        employee.must_change_password = True

        if commit:
            employee.save()

        return employee


class EmployeeEditForm(BaseEmployeeForm):
    class Meta:
        model = Employee
        fields = [
            "name",
            "address",
            "job_title",
            "salary_rate",
            "contact_number",
            "date_hired",
            "role",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_ui()