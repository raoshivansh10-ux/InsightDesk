# Base Image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=wsgi.py

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create directories for DB instance and uploads with safe permissions
RUN mkdir -p /app/instance /app/uploads

# Create a non-root user and group
RUN groupadd -r flask && useradd -r -g flask flask \
    && chown -R flask:flask /app

# Switch to the non-root user
USER flask

# Expose port
EXPOSE 5000

# Gunicorn start command (bind to 0.0.0.0:5000, 4 workers)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:app"]
