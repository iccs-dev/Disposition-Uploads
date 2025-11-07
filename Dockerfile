# Use the official Python image as the base image
# FROM python:3.13
FROM python:3.11-slim
# Set the working directory
WORKDIR /app

# Copy the project files to the container
COPY . /app

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port
EXPOSE 8540

# Run Gunicorn server
CMD ["gunicorn", "--bind", "0.0.0.0:8540", "--workers=4", "--threads=2", "--timeout=60", "--graceful-timeout=30", "--keep-alive=5", "Disposition_Uploads.wsgi:application"]

