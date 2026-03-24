# Course Onboarding Service

Professional Python-based pipeline for migrating Canvas course exports (IMSCC) into the EduvateHub custom LMS (MERN stack).

## Prerequisites
- Python 3.11+
- MongoDB instance
- AWS S3 bucket (for course assets)

## Installation
```bash
pip install -r requirements.txt
```

## Configuration
Copy `.env.example` to `.env` and fill in your credentials. All sensitive IDs and ports are now centralized here.

## Running the Service

### 1. Unified CLI (`cli.py`)
A single interface for all specialized ingestion tasks.
```bash
# Ingest local ZIP
python cli.py ingest-zip path/to/course.zip --uni <ID> --author <ID>

# Batch ingest from S3
python cli.py ingest-s3 --workers 4

# Ingest via Canvas API
python cli.py ingest-canvas --course-id <CANVAS_ID>
```

### 2. API Server (`server.py`)
Starts the hardened FastAPI server on **port 5009**.
```bash
python server.py
```
- **Port**: 5009 (Standardized)
- **Documentation**: http://localhost:5009/docs
- **Endpoints**: `/migrate` (ZIP), `/migrate-canvas` (API), `/jobs/{task_id}` (Status).

## Internal Package Structure
All source code resides in `src/`. The architecture uses the **Adapter Pattern** for multiple sources and a unified **Pipeline** with **MongoDBExporter** for persistence and job tracking.
