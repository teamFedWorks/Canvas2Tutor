import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for package imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load .env
load_dotenv(".env")

from edu_onboarding.core.pipeline import MigrationPipeline
from edu_onboarding.observability.logger import get_logger

logger = get_logger(__name__)

def main():
    """Manual ingestion of a local course folder."""
    parser = argparse.ArgumentParser(description="Manual Local Folder Ingestion")
    parser.add_argument("folder", help="Path to the extracted course folder")
    parser.add_argument("--uni", default="64f1a2b3c4d5e6f7a8b9c0d1", help="University ID")
    parser.add_argument("--author", default="64f1a2b3c4d5e6f7a8b9c0d2", help="Author ID")
    args = parser.parse_args()

    course_path = Path(args.folder)
    if not course_path.exists() or not course_path.is_dir():
        print(f"ERROR: Folder not found at {course_path}")
        return

    print("=" * 80)
    print("MANUAL FOLDER INGESTION")
    print("=" * 80)
    print(f"Source Folder: {course_path.absolute()}")
    print(f"University:    {args.uni}")
    print(f"Author:        {args.author}")
    print()

    try:
        # Initialize pipeline directly with the folder path
        pipeline = MigrationPipeline(
            course_directory=course_path,
            university_id=args.uni,
            author_id=args.author
        )

        print("[START] Running migration pipeline...")
        report = pipeline.run()

        if report.status.value == "success":
            print("\n" + "=" * 80)
            print("INGESTION SUCCESSFUL")
            print("=" * 80)
            print(f"Course Title: {report.source_course_title}")
            print(f"Total Time:   {report.execution_time_seconds:.2f}s")
            print("-" * 80)
            print("Content Summary:")
            for item, count in report.migrated_content_counts.items():
                print(f"  - {item.title()}: {count}")
        else:
            print("\n" + "=" * 80)
            print("INGESTION FAILED")
            print("=" * 80)
            for error in report.all_errors:
                print(f"  [!] {error}")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] {str(e)}")
        logger.exception("Manual folder ingestion failed")

if __name__ == "__main__":
    main()
