# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8080 (Standard for Google Cloud Run / Cloud Providers)
# Note: The app will read the $PORT env var and listen on that port automatically.
EXPOSE 8080

# Define environment variable
# ensuring output is sent directly to terminal without buffering
ENV PYTHONUNBUFFERED=1

# Run server.py when the container launches
# This script handles the 'PORT' environment variable automatically
CMD ["python", "server.py"]
