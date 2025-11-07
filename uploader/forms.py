from django import forms
from .models import UploadedFile

class UploadFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['process', 'file']

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            allowed_extensions = ['.csv', '.xlsx']
            if not any(file.name.endswith(ext) for ext in allowed_extensions):
                raise forms.ValidationError("Only CSV, and XLSX files are allowed.")
        return file
