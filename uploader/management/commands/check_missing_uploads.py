from django.core.management.base import BaseCommand
from django.conf import settings
from uploader.models import UploadStatus
import pandas as pd
import os
from datetime import date

class Command(BaseCommand):
    help = "Check which processes have missing uploads for today."

    def handle(self, *args, **kwargs):
        today = date.today()

        # Get all processes from process.csv
        process_csv = os.path.join(settings.MEDIA_ROOT, 'process', 'process.csv')
        processes = []
        if os.path.exists(process_csv):
            df = pd.read_csv(process_csv, header=None)
            processes = df[0].dropna().tolist()

        for process in processes:
            exists = UploadStatus.objects.filter(process=process, date=today, status='Uploaded').exists()
            if not exists:
                UploadStatus.objects.update_or_create(
                    process=process,
                    date=today,
                    defaults={'status': 'Missing', 'uploaded_file': None}
                )

        self.stdout.write(self.style.SUCCESS("Missing upload check completed."))
