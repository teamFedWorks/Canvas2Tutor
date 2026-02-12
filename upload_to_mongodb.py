#!/usr/bin/env python3
"""
MongoDB Upload Script

Standalone script to upload converted Tutor LMS courses to MongoDB.
Replaces the JavaScript-based Coursesconvert.js.

Usage:
    python upload_to_mongodb.py <course_json_path> [--env-file .env]
    
Example:
    python upload_to_mongodb.py ./cs-1143/tutor_lms_output/tutor_course.json
    python upload_to_mongodb.py ./output/tutor_course.json --env-file .env
"""

import sys
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.config.mongodb_config import MongoDBConfig
from src.exporters.mongodb_uploader import MongoDBUploader


def main():
    """Main entry point for MongoDB upload script."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Upload converted Tutor LMS course to MongoDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python upload_to_mongodb.py ./cs-1143/tutor_lms_output/tutor_course.json
  python upload_to_mongodb.py ./output/tutor_course.json --env-file .env
  
Environment Variables:
  MONGODB_URI              - MongoDB connection string (required)
  MONGODB_DATABASE         - Database name (default: tutor_lms)
  MONGODB_COURSE_COLLECTION - Course collection name (default: courses)
  MONGODB_CURRICULUM_COLLECTION - Curriculum collection name (default: curriculum_items)
        """
    )
    
    parser.add_argument(
        'course_json',
        type=str,
        help='Path to tutor_course.json file'
    )
    
    parser.add_argument(
        '--env-file',
        type=str,
        default='.env',
        help='Path to .env file (default: .env)'
    )
    
    args = parser.parse_args()
    
    # Validate course JSON path
    course_json_path = Path(args.course_json)
    if not course_json_path.exists():
        print(f"❌ Error: Course JSON file not found: {course_json_path}")
        sys.exit(1)
    
    # Check for .env file
    env_file = Path(args.env_file)
    if not env_file.exists():
        print(f"⚠️ Warning: .env file not found at {env_file}")
        print("   Make sure MONGODB_URI environment variable is set.")
        env_file = None
    
    print("=" * 80)
    print("MONGODB UPLOAD - TUTOR LMS COURSE")
    print("=" * 80)
    print()
    print(f"Course JSON: {course_json_path}")
    print(f"Env File: {env_file if env_file else 'Not specified (using environment variables)'}")
    print()
    
    # Load configuration
    config = MongoDBConfig(env_file)
    
    # Create uploader
    uploader = MongoDBUploader(config)
    
    try:
        # Connect to MongoDB
        if not uploader.connect():
            print("\n❌ Failed to connect to MongoDB.")
            print("\nTroubleshooting:")
            print("1. Check that MONGODB_URI is set correctly in .env or environment")
            print("2. Verify MongoDB server is running and accessible")
            print("3. Check network connectivity and firewall settings")
            sys.exit(1)
        
        print()
        
        # Upload course
        success = uploader.upload_course(course_json_path)
        
        if success:
            print()
            print("=" * 80)
            print("UPLOAD COMPLETE")
            print("=" * 80)
            print(f"✅ Course successfully uploaded to MongoDB")
            print(f"   Database: {config.database_name}")
            print(f"   Course Collection: {config.course_collection}")
            print(f"   Curriculum Collection: {config.curriculum_collection}")
            print("=" * 80)
            sys.exit(0)
        else:
            print()
            print("=" * 80)
            print("UPLOAD FAILED")
            print("=" * 80)
            print("❌ Course upload failed. See error messages above.")
            print("=" * 80)
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Upload cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Always disconnect
        uploader.disconnect()


if __name__ == "__main__":
    main()
