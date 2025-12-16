from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import UploadFileForm
from .models import UploadedFile
from .utils import validate_file
from .utils import clean
from django.conf import settings
import os
import csv
import shutil
import logging
import pandas as pd

def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("upload_file")
        else:
            return render(request, "login.html", {"error": "Invalid username or password"})

    return render(request, "login.html")

def user_logout(request):
    logout(request)
    return redirect("login")

@login_required
def upload_file(request):
    message = ""
    error = ""

    # Read options from media/process/process.csv
    process_options = []
    csv_path = os.path.join(settings.MEDIA_ROOT, 'process', 'process.csv')
    if os.path.exists(csv_path):
        with open(csv_path, newline='') as f:
            reader = csv.reader(f)
            process_options = [row[0] for row in reader if row]

    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            process_name = request.POST.get("process") 
            is_valid, msg = validate_file(uploaded_file, process_name)

            if is_valid:
                selected_process = request.POST.get("process")
                if not selected_process:
                    error = "Please select a process."
                else:
                    uploaded_file_instance = UploadedFile(
                        file=uploaded_file,
                        user=request.user,
                        process=selected_process
                    )
                    uploaded_file_instance.save()
                    message = "File uploaded successfully!"
                    file_path = uploaded_file_instance.file.path
                    success, clean_msg, cleaned_file_path  = clean(file_path, selected_process)
                    if not success:
                        error = f"Upload succeeded but cleaning failed: {clean_msg}"
                        logging.error(error)
                    else:
                        message = "File uploaded and cleaned successfully!"
                        logging.info("Clean successful - about to copy cleaned file")

                        try:
                            # Extract Raw Date from cleaned file (to track which date’s data was uploaded)
                            df = pd.read_csv(cleaned_file_path)
                            if 'Raw Date' in df.columns:
                                raw_dates = df['Raw Date'].dropna().unique()
                                for date_str in raw_dates:
                                    try:
                                        parsed_date = pd.to_datetime(date_str, format='%d-%m-%Y').date()
                                        # Update or create status entry
                                        UploadStatus.objects.update_or_create(
                                            process=selected_process,
                                            date=parsed_date,
                                            defaults={
                                                'status': 'Uploaded',
                                                'uploaded_file': uploaded_file_instance
                                            }
                                        )
                                    except Exception as e:
                                        logging.error(f"Invalid Raw Date '{date_str}' for process {selected_process}: {e}")
                        except Exception as e:
                            logging.error(f"Could not read cleaned file for status tracking: {e}")


                        logging.info(f"cleaned_file_path: {cleaned_file_path}")
                        

                        try:
                            safe_process = selected_process.replace(" ", "_")
                            destination_dir = os.path.join('/Disposition_Portal_Data', safe_process, 'APR_Clean')
                            os.makedirs(destination_dir, exist_ok=True)

                            logging.info(f"Checking if file exists: {cleaned_file_path}")
                            logging.info(f"os.path.exists: {os.path.exists(cleaned_file_path)}")

                            if not os.path.exists(cleaned_file_path ):
                                logging.error(f"File does not exist: {cleaned_file_path }")
                            else:
                                map_path = os.path.join(settings.MEDIA_ROOT, 'Map', 'map.csv')
                                if os.path.exists(map_path):
                                    mapping_df = pd.read_csv(map_path, header=None)
                                    process_row = mapping_df[mapping_df[0].str.strip().str.lower() == selected_process.strip().lower()]

                                    if not process_row.empty:
                                        pn = str(process_row.iloc[0, 4]).strip()   # 5th column
                                        original_filename = os.path.basename(cleaned_file_path)
                                        new_filename = f"{pn}%{original_filename}"
                                        destination_path = os.path.join(destination_dir, new_filename)

                                        shutil.copy2(cleaned_file_path, destination_path)
                                        logging.info(f"Copied '{cleaned_file_path}' to '{destination_path}'")
                                    else:
                                        logging.error(f"No mapping row found for process: {selected_process}")
                                else:
                                    logging.error(f"Mapping file not found: {map_path}")

                        except Exception as e:
                            error = f"File cleaned but failed to copy to destination: {str(e)}"
                            logging.error(error)
            
            else:
                error = f"Upload failed: {msg}"
        else:
            error = f"Upload failed: {form.errors['file'][0]}"
    else:
        form = UploadFileForm()

    files = UploadedFile.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'upload.html', {
        'form': form,
        'files': files,
        'message': message,
        'error': error,
        'process_options': process_options  # Pass options to template
    })
