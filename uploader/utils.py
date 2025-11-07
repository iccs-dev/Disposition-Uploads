import pandas as pd
import numpy as np
import os
from django.conf import settings
import datetime
import logging
from django.core.mail import send_mail

# Configure logging once (ideally in settings or a main script)
LOG_DIR = os.path.join(settings.MEDIA_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'cleaning_errors.log')

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

ALLOWED_EXTENSIONS = ['csv', 'xlsx']

def validate_file(uploaded_file, process_name):
    """Validate file by checking required columns (case-insensitive, ignore order, allow extra)."""

    file_ext = uploaded_file.name.split('.')[-1].lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type: {file_ext}. \nAllowed types: .csv, .xlsx"

    reference_file_path = os.path.join(settings.MEDIA_ROOT, "reference", process_name, "format.xlsx")
    if not os.path.exists(reference_file_path):
        return False, f"Reference format file not found for process: {process_name}"

    try:
        # Read only header from reference
        try:
            reference_df = pd.read_excel(reference_file_path, engine="openpyxl", nrows=0)
        except Exception as e:
            return False, "Could not read reference format file. "  #{str(e)}

        if len(reference_df.columns) == 0:
            return False, "Reference format file has no column headers."

        # Read only header from uploaded file
        try:
            if file_ext == "csv":
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                uploaded_df = pd.read_excel(uploaded_file, engine="openpyxl", nrows=0)
        except Exception as e:
            return False, "Could not read uploaded file"

        if len(uploaded_df.columns) == 0:
            return False, "Uploaded file has no column headers."

        # Normalize column names
        reference_columns = [str(col).strip().lower() for col in reference_df.columns]
        uploaded_columns = [str(col).strip().lower() for col in uploaded_df.columns]


        # Compare column names
        if reference_columns == uploaded_columns:
            return True, "File is valid"
        else:
            return False, "Column mismatched. \nPlease check the format."
            # return False, f"Column mismatch: Expected {reference_columns}, but got {uploaded_columns}"


    except Exception as e:
        return False, f"Error validating the file : {e}"



def time_to_minutes(time_val):

    # Handle string inputs
    if isinstance(time_val, str):
        try:
            h, m, s = map(int, time_val.split(":"))
            return h * 60 + m + s / 60
        except ValueError:
            return 0

    # Handle timedelta or datetime.time
    elif isinstance(time_val, datetime.time):
        return time_val.hour * 60 + time_val.minute + time_val.second / 60

    elif isinstance(time_val, pd.Timedelta):
        total_seconds = time_val.total_seconds()
        return total_seconds / 60

    return time_val  # Default fallback

def send_failure_email(subject, message):
    """Send an email when cleaning fails."""
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,  # Make sure this is set in Django settings
            ['ishita.jain@iccs.in'],
            fail_silently=False
        )
    except Exception as mail_err:
        logging.error(f"Failed to send error email: {mail_err}")


# JVVNL-specific time normalization
JVVNL_TIME_COLS = [
    "TOTAL_LOGIN_TIME",
    "TOTAL_BREAK_TIME",
    "TOTAL_RING_DELAY",
    "TOTAL_TALK_TIME",
    "TOTAL_WRAP_UP_TIME",
    "AVERAGE_TALK_TIME",
    "AVERAGE_WRAP_UP_TIME",
    "AVERAGE_HANDLING_TIME",
]

def normalize_jvvnl_time(val):

    # Convert time like '00:02.7' → '00:00:02'
    # Convert '02:36.3' → '00:02:36'
    # Blank/invalid → '00:00:00'

    try:
        if pd.isna(val) or str(val).strip() == "":
            return "00:00:00"

        val = str(val).strip()

        # Handle fractional seconds
        if "." in val:
            main, _ = val.split(".", 1)
        else:
            main = val

        parts = main.split(":")
        if len(parts) == 2:  # mm:ss
            mm, ss = parts
            return f"00:{int(mm):02d}:{int(ss):02d}"
        elif len(parts) == 3:  # hh:mm:ss
            hh, mm, ss = parts
            return f"{int(hh):02d}:{int(mm):02d}:{int(ss):02d}"

        return "00:00:00"

    except Exception:
        return "00:00:00"

def clean(file_path, process_name):
    try:

        # Step 1: Load mapping
        map_path = os.path.join(settings.MEDIA_ROOT, 'Map', 'map.csv')
        if not os.path.exists(map_path):
            msg = "Mapping file not found"
            send_failure_email(
                f"Cleaning Failed - {process_name}",
                f"File: {file_path}\nReason: {msg}"
            )
            return False, "Mapping file not found", file_path

        mapping_df = pd.read_csv(map_path, header=None)
        process_row = mapping_df[mapping_df[0].str.strip().str.lower() == process_name.strip().lower()]
        
        if process_row.empty:
            msg = f"No mapping found for process: {process_name}"
            send_failure_email(
                f"Cleaning Failed - {process_name}",
                f"File: {file_path}\nReason: {msg}"
            )
            return False, f"No mapping found for process: {process_name}", file_path

        login_col = process_row.iloc[0, 1]
        break_col = process_row.iloc[0, 2]
        first_login_col = process_row.iloc[0, 3]
       
        # Step 2: Load uploaded file
        ext = file_path.split('.')[-1].lower()
        if ext == 'csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, engine='openpyxl')
        
        # Special handling for JVVNL
        if process_name.strip().lower() == "jvvnl":
            for col in JVVNL_TIME_COLS:
                if col in df.columns:
                    df[col] = df[col].apply(normalize_jvvnl_time)

        # Step 3: Check if required columns exist
        # if login_col not in df.columns or break_col not in df.columns or first_login_col not in df.columns:
        #     msg = "One or more required columns not found"
        #     send_failure_email(
        #         f"Cleaning Failed - {process_name}",
        #         f"File: {file_path}\nReason: {msg}"
        #     )
        #     return False, "One or more required columns not found", file_path
        
        # Step 3: Check if required columns exist (case-insensitive, strip spaces)
        df_columns_lower = [str(c).strip().lower() for c in df.columns]

        if (str(login_col).strip().lower() not in df_columns_lower or
            str(break_col).strip().lower() not in df_columns_lower or
            str(first_login_col).strip().lower() not in df_columns_lower):
            msg = "One or more required columns not found"
            send_failure_email(
                f"Cleaning Failed - {process_name}",
                f"File: {file_path}\nReason: {msg}"
            )
            return False, "One or more required columns not found", file_path

        # Step 5: Remove rows after "Total" or "Admin"
        exempted_processes = ['Mpokket Collection APR', 'Mpokket Collection Breakcode']

        if process_name.strip() in exempted_processes:
            import re
            # Match whole word 'admin', 'total', 'grand total' only (not if followed by parentheses, dash, etc.)
            pattern = re.compile(r'\b(admin|total|grand total)\b(?![\(\-\w])', re.IGNORECASE)

            def should_exclude(cell):
                if not isinstance(cell, str):
                    return False
                return bool(pattern.search(cell.strip()))

            mask = df.astype(str).applymap(should_exclude).any(axis=1)
            total_row_index = df[mask].index
        else:
            mask = df.astype(str).apply(lambda row: row.str.contains('Total|Admin', case=False, na=False), axis=1)
            total_row_index = df[mask.any(axis=1)].index

        if len(total_row_index) > 0:
            df = df.iloc[:total_row_index[0]]

        # New Step: Remove rows containing "Campaign Summary"
        df = df[~df.astype(str).apply(lambda row: row.str.contains("Campaign Summary|Summary|NoAgent", case=False, na=False)).any(axis=1)]

        if process_name.strip().lower() == "meity" and "AGENT_NAME" in df.columns:
            df = df[~df["AGENT_NAME"].astype(str).str.strip().str.lower().isin(["null", "nan", "none", ""])]

        if process_name.strip().lower() == "dish tv-backend" or process_name.strip().lower() == "dish ib-chennai":
            # Drop last row 
            df = df.iloc[:-1] if not df.empty else df
        
        # Special cleaning for D2H & Dish 44 - Server
        if process_name.strip().lower() in ["d2h & dish 44 - server"]:
            df = df[~df.astype(str).apply(lambda row: row.str.contains("Day Total", case=False, na=False)).any(axis=1)]

        # Step 4: Time conversion and filtering
        df["Login Duration (minutes)"] = df[login_col].apply(time_to_minutes)
        df["Total Break Duration (minutes)"] = df[break_col].apply(time_to_minutes)
        df["Minutes"] = df["Login Duration (minutes)"] - df["Total Break Duration (minutes)"]
        # df = df[df["Minutes"] != 0.0]
        
        # Step 7: Add Raw Date column
        # df['Raw Date'] = pd.to_datetime(df[first_login_col], errors='coerce').dt.strftime('%d-%m-%y')
        # df['Raw Date'] = pd.to_datetime(df[first_login_col], dayfirst=True, errors='coerce').dt.strftime('%d-%m-%y')

        def extract_or_convert(date_val):
            try:
                if isinstance(date_val, str):
                    # Case 1: Range "08-09-2025 - 09-09-2025"
                    if ' - ' in date_val:
                        return pd.to_datetime(date_val.split(' - ')[0], errors='coerce').strftime('%d-%m-%Y')
                    
                    # Case 2: Datetime with month name "08-Sep-25 00:43:24"
                    return pd.to_datetime(date_val, dayfirst=True, errors='coerce').strftime('%d-%m-%Y')
                
                # Case 3a: Excel serial date (int/float)
                if isinstance(date_val, (int, float)):
                    excel_base = pd.Timestamp('1899-12-30')
                    dt = excel_base + pd.to_timedelta(date_val, unit='D')
                    return dt.strftime('%d-%m-%Y')
                
                # Case 3b: Direct datetime/other formats
                return pd.to_datetime(date_val, dayfirst=True, errors='coerce').strftime('%d-%m-%Y')
            
            except Exception:
                return None
        # def extract_or_convert(date_val):
        #     if isinstance(date_val, str) and ' - ' in date_val:
        #         # take the first date and format as dd-mm-yyyy
        #         parsed = pd.to_datetime(date_val.split(' - ')[0], errors='coerce')
        #     else:
        #         # convert directly
        #         parsed = pd.to_datetime(date_val, dayfirst=True, errors='coerce')

        #     if pd.isna(parsed):
        #         return None   # or "" if you want string
        #     return parsed.strftime('%d-%m-%Y')
        
        df['Raw Date'] = df[first_login_col].apply(extract_or_convert)
        df['Minutes'] = np.ceil(df['Minutes']).fillna(0).astype(int)

        

        # Step 8: Drop intermediate calculation columns
        df.drop(['Login Duration (minutes)', 'Total Break Duration (minutes)', 'Minutes'], axis=1, inplace=True, errors='ignore')

        # Step 9: Drop empty columns before saving
        df.dropna(axis=1, how='all', inplace=True)       # Drop columns with all NaN
        df = df.loc[:, ~(df == '').all()]                # Drop columns with all empty strings

        # Step 9: Save final cleaned file
        clean_dir = os.path.join(settings.MEDIA_ROOT, 'clean', process_name, 'APR_Clean')
        os.makedirs(clean_dir, exist_ok=True)
        cleaned_path = os.path.join(clean_dir, os.path.basename(file_path).rsplit('.', 1)[0] + '.csv')
        df.to_csv(cleaned_path, index=False)

        return True, f"Cleaned file saved at: {cleaned_path}", cleaned_path

    except Exception as e:
        error_msg = f"Error during cleaning for process '{process_name}', file '{os.path.basename(file_path)}': {str(e)}"
        send_failure_email(
            f"Cleaning Failed - {process_name}",
            f"File: {file_path}\nError: {str(e)}"
        )
        logging.error(
            f"Error during cleaning for process '{process_name}', "
            f"file '{os.path.basename(file_path)}': {str(e)}"
        )
        return False, f"Error during cleaning: {str(e)}", file_path


