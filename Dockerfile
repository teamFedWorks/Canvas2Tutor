# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for lxml and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create directory for course storage and output
RUN mkdir -p /app/storage/uploads /app/storage/outputs

# Expose the API port
EXPOSE 5009

# Set environment variables
ENV PYTHONPATH=/app
ENV STORAGE_DIR=/app/storage
ENV PORT=5009

# Start the FastAPI application via the unified server entry point
CMD ["python", "server.py"]
