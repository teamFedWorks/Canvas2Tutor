# Course Onboarding Service

Professional Python-based pipeline for migrating Canvas course exports (IMSCC) into the EduvateHub custom LMS (MERN stack).

## Prerequisites
- Python 3.9+
- MongoDB instance
- AWS S3 bucket (for course assets)

## Installation
```bash
pip install -r requirements.txt
```

## Configuration
Copy `.env.example` to `.env` and fill in your credentials:
- `MONGODB_URI`: Connection string for MongoDB.
- `S3_ASSETS_BUCKET`: Target S3 bucket for assets.
- `S3_CDN_BASE_URL`: (Optional) CDN URL for asset rewriting.

## Running the Service

### 1. API Migration Service (FastAPI)
Starts the background processing service with HTTP endpoints.
```bash
python main_api.py
```
- **Port**: 8000
- **Documentation**: http://localhost:8000/docs
- **Endpoints**: `/migrate` (Upload ZIP), `/migrate-s3` (Remote Key).

### 2. Single Course Ingestion (CLI)
Used for direct ingestion of a local ZIP file.
```bash
python main_ingestion.py
```

### 3. S3 Batch Ingestion (Parallel CLI)
Processes all course packages found in your `S3_INGESTION_BUCKET` using multiple threads for speed.
```bash
# Process all courses with 4 parallel workers (fastest)
python main_s3_batch.py --workers 4

# Manual Process: Process specific S3 keys only
python main_s3_batch.py --keys courses/cs-101.zip courses/math-202.zip
```

### 4. Direct Folder Ingestion (Manual)
If you have an extracted course folder (no ZIP), use this:
```bash
python main_manual_folder.py <path_to_folder> --uni <id> --author <id>
```

### 5. Local ZIP Ingestion (Manual)
Used for single local ZIP file migration.
```bash
python main_ingestion.py
```

### 6. Manual JSON Record Upload
Directly upload a pre-converted `tutor_course.json` document.
```bash
python main_upload.py <path_to_json>
```

## Internal Package Structure
All source code resides in `src/edu_onboarding/`. Standardized sub-packages handle `api`, `core/pipeline`, `parsers`, `models`, and `exporters`.
