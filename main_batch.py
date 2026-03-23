import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv(".env")

# Add src to path for package imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from edu_onboarding.worker.ingestion_worker import IngestionWorker

# Configuration
s3_bucket = os.getenv("S3_CDN_BUCKET", "eduvatehub-assets-cdn")
cdn_url = os.getenv("CDN_URL", "https://assets.eduvatehub.com")
worker = IngestionWorker(s3_bucket=s3_bucket, cdn_url=cdn_url)

university_id = "64f1a2b3c4d5e6f7a8b9c0d1"
author_id = "64f1a2b3c4d5e6f7a8b9c0d2"

upload_dir = Path(r"B:\EduvateHub\CourseOnboarding\storage\uploads")

courses_to_run = [
    "ent-1001", "ent-1777", "it-1104", "it-2105", "it-2510", 
    "it-2620", "it-3101", "it-3301", "it-3310", "it-4016"
]

for code in courses_to_run:
    print(f"\n--- BATCH INGESTION: {code.upper()} ---")
    zip_path = upload_dir / f"{code}_fixed.zip"
    if not zip_path.exists():
        print(f"ERROR: {code} ZIP NOT FOUND at {zip_path}")
        continue
    
    try:
        result = worker.process_package(zip_path, university_id, author_id, title_override=code.upper())
        if result.get("status") == "success":
            print(f"SUCCESS {code.upper()}: {result.get('course_id')} - {result.get('title')}")
        else:
            print(f"FAILED {code.upper()}: {result.get('error')}")
    except Exception as e:
        print(f"CRASHED {code.upper()}: {e}")

print("\n--- BATCH COMPLETE ---")
