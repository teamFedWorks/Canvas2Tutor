"""
MongoDB Uploader Module

Uploads converted Tutor LMS courses to MongoDB database.
Replaces the JavaScript-based Coursesconvert.js with Python implementation.
"""

import json
import re
import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

try:
    from pymongo import MongoClient
    from bson import ObjectId
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    print("Warning: pymongo not installed. Install with: pip install pymongo")

from ..config.mongodb_config import MongoDBConfig


class MongoDBUploader:
    """Handles uploading Tutor LMS courses to MongoDB."""
    
    def __init__(self, config: MongoDBConfig):
        """
        Initialize MongoDB uploader.
        
        Args:
            config: MongoDB configuration
        """
        if not PYMONGO_AVAILABLE:
            raise ImportError("pymongo is required. Install with: pip install pymongo")
        
        self.config = config
        self.client: Optional[MongoClient] = None
        self.db = None
        
    def connect(self) -> bool:
        """
        Connect to MongoDB.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            print("🔌 Connecting to MongoDB...")
            
            # Validate configuration
            is_valid, error_msg = self.config.validate()
            if not is_valid:
                print(f"❌ Configuration error: {error_msg}")
                return False
            
            # Create MongoDB client
            self.client = MongoClient(
                self.config.mongodb_uri,
                **self.config.get_connection_options()
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[self.config.database_name]
            
            print(f"✅ Connected to MongoDB database: {self.config.database_name}")
            return True
            
        except Exception as e:
            print(f"❌ MongoDB connection failed: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("👋 MongoDB connection closed.")
    
    @staticmethod
    def slugify(text: str) -> str:
        """
        Convert text to URL-friendly slug.
        
        Args:
            text: Text to slugify
            
        Returns:
            Slugified text
        """
        if not text:
            return f'untitled-{int(time.time() * 1000)}'
        
        # Convert to lowercase and strip whitespace
        slug = text.lower().strip()
        
        # Replace spaces with hyphens
        slug = re.sub(r'\s+', '-', slug)
        
        # Remove non-word characters (except hyphens)
        slug = re.sub(r'[^\w\-]+', '', slug)
        
        # Replace multiple hyphens with single hyphen
        slug = re.sub(r'\-\-+', '-', slug)
        
        # Add random number to prevent duplicates
        import random
        slug = f"{slug}-{random.randint(100, 999)}"
        
        return slug
    
    @staticmethod
    def determine_type(title: str) -> str:
        """
        Determine content type based on title.
        
        Args:
            title: Content title
            
        Returns:
            Content type: 'Quiz', 'Assignment', or 'Lesson'
        """
        title_lower = title.lower()
        
        if 'quiz' in title_lower:
            return 'Quiz'
        elif 'assignment' in title_lower or 'project' in title_lower:
            return 'Assignment'
        else:
            return 'Lesson'
    
    def transform_course_data(self, tutor_course_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform Tutor LMS JSON to MongoDB schema format.
        
        Args:
            tutor_course_data: Tutor LMS course data from JSON
            
        Returns:
            Dictionary with 'course_document' and 'curriculum_items'
        """
        try:
            # Generate IDs
            course_id = ObjectId()
            author_id = ObjectId()
            
            all_curriculum_items = []
            course_curriculum_structure = []
            
            # Extract modules/topics from the course data
            # The structure should have 'modules' or 'topics' at the top level
            modules = tutor_course_data.get('modules', [])
            
            # Handle nested structure (like in the JS code)
            if modules and isinstance(modules, list) and len(modules) > 0:
                # Check if first module has nested items
                if isinstance(modules[0], dict) and 'items' in modules[0]:
                    real_modules = modules[0].get('items', [])
                else:
                    real_modules = modules
            else:
                # Try 'topics' key as alternative
                real_modules = tutor_course_data.get('topics', [])
            
            if not real_modules:
                print("⚠️ No modules/topics found. Check JSON structure.")
                return None
            
            print(f"🔍 Found {len(real_modules)} modules to process...")
            
            # Process each module/topic
            for source_module in real_modules:
                topic_id = ObjectId()
                module_items_references = []
                
                # Get module title
                module_title = source_module.get('title', 'Untitled Module')
                
                # Process items inside the module
                module_items = source_module.get('items', [])
                
                for source_item in module_items:
                    item_id = ObjectId()
                    item_title = source_item.get('title', 'Untitled Item')
                    item_type = self.determine_type(item_title)
                    item_slug = self.slugify(item_title)
                    
                    # Create curriculum item document
                    curriculum_item = {
                        '_id': item_id,
                        'courseId': course_id,
                        'topicId': topic_id,
                        'title': item_title,
                        'slug': item_slug,
                        'type': item_type,
                        'isHidden': False,
                        'content': source_item.get('content', '<p>No content provided.</p>'),
                    }
                    
                    all_curriculum_items.append(curriculum_item)
                    
                    # Create reference for course schema
                    module_items_references.append({
                        'itemId': item_id,
                        'itemType': item_type,
                        'title': item_title,
                        'slug': item_slug
                    })
                
                # Add topic to course curriculum structure
                course_curriculum_structure.append({
                    '_id': topic_id,
                    'title': module_title,
                    'summary': source_module.get('description', ''),
                    'locked': False,
                    'items': module_items_references
                })
            
            # Create course document
            course_title = tutor_course_data.get('title', 'Imported Course')
            course_document = {
                '_id': course_id,
                'title': course_title,
                'courseUrl': self.slugify(course_title),
                'description': tutor_course_data.get('description', 'Imported Course Content'),
                'featuredImage': 'https://placehold.co/600x400?text=Course+Image',
                'introVideo': '',
                'authorId': author_id,
                'authorName': 'Admin',
                'pricingModel': 'Free',
                'price': 0,
                'categories': ['Imported'],
                'difficultyLevel': 'All Levels',
                'curriculum': course_curriculum_structure,
                'isPublic': True,
                'isDraft': False,
                'createdAt': datetime.utcnow(),
                'updatedAt': datetime.utcnow(),
            }
            
            return {
                'course_document': course_document,
                'curriculum_items': all_curriculum_items
            }
            
        except Exception as e:
            print(f"❌ Data transformation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def upload_course(self, course_json_path: Path) -> bool:
        """
        Upload course from JSON file to MongoDB.
        
        Args:
            course_json_path: Path to tutor_course.json file
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            # Load JSON file
            print(f"📖 Reading course data from {course_json_path}...")
            with open(course_json_path, 'r', encoding='utf-8') as f:
                course_data = json.load(f)
            
            # Transform data
            print("🔄 Transforming data to MongoDB schema...")
            transformed = self.transform_course_data(course_data)
            
            if not transformed:
                print("❌ Data transformation failed.")
                return False
            
            course_document = transformed['course_document']
            curriculum_items = transformed['curriculum_items']
            
            # Insert curriculum items
            print(f"🚀 Inserting {len(curriculum_items)} curriculum items...")
            curriculum_collection = self.db[self.config.curriculum_collection]
            
            if curriculum_items:
                result = curriculum_collection.insert_many(curriculum_items)
                print(f"✅ Inserted {len(result.inserted_ids)} curriculum items successfully.")
            else:
                print("⚠️ No curriculum items to insert.")
            
            # Insert course document
            print(f"🚀 Creating course: \"{course_document['title']}\"...")
            course_collection = self.db[self.config.course_collection]
            course_collection.insert_one(course_document)
            print("✅ Course document created successfully.")
            
            print("\n🎉 Upload complete!")
            print(f"   Course ID: {course_document['_id']}")
            print(f"   Course URL: {course_document['courseUrl']}")
            print(f"   Total Items: {len(curriculum_items)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Upload failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def upload_to_mongodb(course_json_path: Path, env_file: Optional[Path] = None) -> bool:
    """
    Convenience function to upload a course to MongoDB.
    
    Args:
        course_json_path: Path to tutor_course.json file
        env_file: Optional path to .env file
        
    Returns:
        True if upload successful, False otherwise
    """
    # Load configuration
    config = MongoDBConfig(env_file)
    
    # Create uploader
    uploader = MongoDBUploader(config)
    
    try:
        # Connect to MongoDB
        if not uploader.connect():
            return False
        
        # Upload course
        success = uploader.upload_course(course_json_path)
        
        return success
        
    finally:
        # Always disconnect
        uploader.disconnect()
