"""
MongoDB Configuration Module

Handles MongoDB connection configuration and environment variable management.
"""

import os
from typing import Optional
from pathlib import Path


class MongoDBConfig:
    """MongoDB configuration manager."""
    
    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize MongoDB configuration.
        
        Args:
            env_file: Optional path to .env file
        """
        # Load environment variables from .env file if provided
        if env_file and env_file.exists():
            self._load_env_file(env_file)
        
        self.mongodb_uri = os.getenv('MONGODB_URI')
        self.database_name = os.getenv('MONGODB_DATABASE', 'tutor_lms')
        self.course_collection = os.getenv('MONGODB_COURSE_COLLECTION', 'courses')
        self.curriculum_collection = os.getenv('MONGODB_CURRICULUM_COLLECTION', 'curriculum_items')
        
    def _load_env_file(self, env_file: Path):
        """Load environment variables from .env file."""
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip().strip('"').strip("'")
                        os.environ[key.strip()] = value
        except Exception as e:
            print(f"Warning: Could not load .env file: {e}")
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.mongodb_uri:
            return False, "MONGODB_URI environment variable is not set"
        
        if not self.mongodb_uri.startswith('mongodb'):
            return False, "MONGODB_URI must start with 'mongodb://' or 'mongodb+srv://'"
        
        return True, None
    
    def get_connection_options(self) -> dict:
        """
        Get MongoDB connection options.
        
        Returns:
            Dictionary of connection options
        """
        return {
            'serverSelectionTimeoutMS': 5000,
            'connectTimeoutMS': 10000,
            'socketTimeoutMS': 10000,
        }
