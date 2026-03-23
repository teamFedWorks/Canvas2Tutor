import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load .env
load_dotenv(".env")

s3_bucket = os.getenv("S3_CDN_BUCKET", "eduvatehub-assets-cdn")
cdn_url = os.getenv("CDN_URL", "https://assets.eduvatehub.com")

# Add src to path for package imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from edu_onboarding.worker.ingestion_worker import IngestionWorker

worker = IngestionWorker(s3_bucket=s3_bucket, cdn_url=cdn_url)

zip_file = Path(r"B:\EduvateHub\CourseOnboarding\storage\uploads\ENT-1001 Intro to Entrepreneurship\ent-1001.zip")
university_id = "64f1a2b3c4d5e6f7a8b9c0d1" # dummy mongo id
author_id = "64f1a2b3c4d5e6f7a8b9c0d2" # dummy mongo id

import traceback

try:
    print(f"Starting ingestion for {zip_file}")
    result = worker.process_package(zip_file, university_id, author_id)
    print("Result:")
    print(result)
except Exception as e:
    with open("error_log.txt", "w") as f:
        traceback.print_exc(file=f)
    print("Failed")

