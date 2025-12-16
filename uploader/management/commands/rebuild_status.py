import os
import pandas as pd
import datetime
import logging
from django.core.management.base import BaseCommand
from uploader.models import UploadedFile, UploadStatus
from django.conf import settings


class Command(BaseCommand):
    help = "Rebuilds UploadStatus records from existing uploaded files."

    def handle(self, *args, **kwargs):
        logging.basicConfig(level=logging.INFO)
        self.stdout.write(self.style.SUCCESS("🔁 Rebuilding UploadStatus table..."))

        count = 0
        failed = 0

        for uf in UploadedFile.objects.all():
            process = uf.process
            file_path = uf.file.path
            cleaned_dir = os.path.join(settings.MEDIA_ROOT, "clean", process, "APR_Clean")

            # try to find cleaned file corresponding to this upload
            cleaned_file = None
            if os.path.exists(cleaned_dir):
                for f in os.listdir(cleaned_dir):
                    if os.path.splitext(os.path.basename(file_path))[0] in f:
                        cleaned_file = os.path.join(cleaned_dir, f)
                        break

            if not cleaned_file or not os.path.exists(cleaned_file):
                self.stdout.write(self.style.WARNING(f"⚠️ No cleaned file found for {process} ({file_path})"))
                failed += 1
                continue

            try:
                # Try reading the cleaned file
                if cleaned_file.endswith(".csv"):
                    df = pd.read_csv(cleaned_file)
                else:
                    df = pd.read_excel(cleaned_file)

                if "Raw Date" in df.columns:
                    raw_dates = df["Raw Date"].dropna().unique()
                    for date_str in raw_dates:
                        parsed_date = pd.to_datetime(date_str, format='%d-%m-%Y', errors="coerce")
                        if pd.notna(parsed_date):
                            UploadStatus.objects.update_or_create(
                                process=process,
                                date=parsed_date.date(),
                                defaults={
                                    "status": "Uploaded",
                                    "uploaded_file": uf,
                                },
                            )
                            count += 1
                else:
                    # fallback if Raw Date missing
                    UploadStatus.objects.update_or_create(
                        process=process,
                        date=datetime.date.today(),
                        defaults={
                            "status": "Uploaded",
                            "uploaded_file": uf,
                        },
                    )
                    count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error reading {cleaned_file}: {e}"))
                failed += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Done. Created/Updated {count} records, {failed} failed."))
