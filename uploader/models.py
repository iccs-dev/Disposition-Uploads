from django.db import models
from django.contrib.auth.models import User
import os

def upload_to_process_folder(instance, filename):
    return os.path.join('uploads', instance.process, filename)

class UploadedFile(models.Model):
    file = models.FileField(upload_to=upload_to_process_folder)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Link file to the user
    process = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.process} - {self.file.name}"

class UploadStatus(models.Model):
    process = models.CharField(max_length=100)
    date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('Uploaded', 'Uploaded'),
            ('Missing', 'Missing')
        ],
        default='Missing'
    )
    uploaded_file = models.ForeignKey(
        'UploadedFile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_entries'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('process', 'date')  # ensure one record per process/date
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.process}: {self.status}"
