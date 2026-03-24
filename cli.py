#!/usr/bin/env python3
"""
EduvateHub Course Onboarding CLI

A unified interface for managing course ingestions (ZIP, S3, Canvas) 
and starting the API server.
"""

import os
import sys
import argparse
import concurrent.futures
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for package imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load .env
load_dotenv(".env")

from worker.ingestion_worker import IngestionWorker
from utils.s3_utils import S3Downloader
from observability.logger import get_logger

logger = get_logger(__name__)


def run_server():
    """Start the FastAPI server."""
    import uvicorn
    from api.main import app
    port = int(os.getenv("PORT", 5009))
    print(f"Starting EduvateHub Onboarding API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)


def ingest_zip(args):
    """Process a local course ZIP."""
    zip_path = Path(args.path)
    if not zip_path.exists():
        print(f"[ERROR] ZIP file not found at {zip_path}")
        return

    worker = _get_worker()
    print(f"[INFO] Starting ingestion for {zip_path.name}...")
    result = worker.ingest(
        source_type="zip",
        payload={
            "zip_path": zip_path,
            "university_id": args.uni,
            "author_id": args.author,
            "force": args.force
        }
    )
    _print_result(result)


def ingest_s3(args):
    """Batch process ZIPs from S3."""
    ingestion_bucket = os.getenv("S3_INGESTION_BUCKET")
    if not ingestion_bucket:
        print("❌ Error: S3_INGESTION_BUCKET not set in .env")
        return

    downloader = S3Downloader(bucket=ingestion_bucket)
    worker = _get_worker()
    
    print(f"[INFO] Scanning S3 bucket: {ingestion_bucket}...")
    s3_keys = downloader.list_courses(prefix=args.prefix)
    if not s3_keys:
        print("[INFO] No .zip files found in S3.")
        return

    print(f"[INFO] Found {len(s3_keys)} packages. Starting parallel ingestion (workers={args.workers})...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(_process_s3_key, key, downloader, worker, args): key 
            for key in s3_keys
        }
        
        success_count = 0
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                if future.result():
                    success_count += 1
            except Exception as e:
                print(f"❌ Error processing {key}: {e}")

    print(f"\n✅ S3 Batch Complete: {success_count}/{len(s3_keys)} successful.")


def ingest_canvas(args):
    """Trigger a Canvas API migration."""
    worker = _get_worker()
    print(f"[INFO] Triggering Canvas API migration for Course ID: {args.course_id}...")
    result = worker.ingest(
        source_type="canvas",
        payload={
            "course_id": args.course_id,
            "university_id": args.uni,
            "author_id": args.author,
            "force": args.force
        }
    )
    _print_result(result)


def _get_worker():
    """Shared worker initialization."""
    s_bucket = os.getenv("S3_CDN_BUCKET")
    c_url = os.getenv("CDN_URL")
    return IngestionWorker(s3_bucket=s_bucket, cdn_url=c_url)


def _process_s3_key(key, downloader, worker, args):
    """Internal helper for S3 parallel worker."""
    temp_dir = Path(f"storage/temp_s3/{os.getpid()}_{hash(key) % 1000}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        local_zip = downloader.download(key, temp_dir)
        result = worker.ingest(
            source_type="zip",
            payload={
                "zip_path": local_zip,
                "university_id": args.uni,
                "author_id": args.author,
                "force": args.force
            }
        )
        if result.get("status") == "success":
            print(f"[SUCCESS] {key}")
            return True
        else:
            print(f"[FAILED] {key}: {result.get('error')}")
            return False
    finally:
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)


def _print_result(result):
    """Standardized result printing."""
    if result.get("status") == "success":
        print(f"[SUCCESS] Ingestion Successful!")
        print(f"   Course ID: {result.get('course_id')}")
        if result.get("deduplicated"):
            print("   (Course already existed, skipped re-import)")
    else:
        print(f"[ERROR] Ingestion Failed: {result.get('error')}")


def main():
    parser = argparse.ArgumentParser(description="EduvateHub Onboarding CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Server command
    subparsers.add_parser("server", help="Start the FastAPI server")

    # Ingest Zip command
    zip_parser = subparsers.add_parser("ingest-zip", help="Ingest a local ZIP")
    zip_parser.add_argument("--path", required=True, help="Path to local .zip file")
    zip_parser.add_argument("--uni", default=os.getenv("DEFAULT_UNIVERSITY_ID", "default_uni"), help="University ID")
    zip_parser.add_argument("--author", default=os.getenv("DEFAULT_AUTHOR_ID", "default_author"), help="Author ID")
    zip_parser.add_argument("--force", action="store_true", help="Force re-import")

    # Ingest S3 command
    s3_parser = subparsers.add_parser("ingest-s3", help="Batch ingest from S3")
    s3_parser.add_argument("--prefix", default="", help="S3 prefix filter")
    s3_parser.add_argument("--workers", type=int, default=4, help="Parallel workers")
    s3_parser.add_argument("--uni", default=os.getenv("DEFAULT_UNIVERSITY_ID", "default_uni"), help="University ID")
    s3_parser.add_argument("--author", default=os.getenv("DEFAULT_AUTHOR_ID", "default_author"), help="Author ID")
    s3_parser.add_argument("--force", action="store_true", help="Force re-import")

    # Ingest Canvas command
    canvas_parser = subparsers.add_parser("ingest-canvas", help="Ingest from Canvas API")
    canvas_parser.add_argument("--course-id", required=True, help="Canvas Course ID")
    canvas_parser.add_argument("--uni", required=True, help="University ID")
    canvas_parser.add_argument("--author", required=True, help="Author ID")
    canvas_parser.add_argument("--force", action="store_true", help="Force re-import")

    args = parser.parse_args()

    if args.command == "server":
        run_server()
    elif args.command == "ingest-zip":
        ingest_zip(args)
    elif args.command == "ingest-s3":
        ingest_s3(args)
    elif args.command == "ingest-canvas":
        ingest_canvas(args)


if __name__ == "__main__":
    main()
