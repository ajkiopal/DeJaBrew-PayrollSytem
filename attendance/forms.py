from django import forms


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Select CSV File",
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".csv",
                "class": "form-control form-control-lg rounded-pill",
                "style": "border: 2px solid #d6ccc2;",
            }
        )
    )