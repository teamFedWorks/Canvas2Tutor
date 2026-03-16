"""
DynamoDB Utilities Module

Handles fetching course metadata from AWS DynamoDB.
"""

import os
from typing import Optional, Dict, Any


def _get_dynamodb_resource():
    """Create and return a boto3 DynamoDB resource using environment credentials."""
    try:
        import boto3
        return boto3.resource(
            'dynamodb',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
        )
    except ImportError:
        raise ImportError("boto3 is required for DynamoDB support. Install with: pip install boto3")


class MetadataProvider:
    """
    Provides course metadata from DynamoDB.
    """

    def __init__(self, table_name: Optional[str] = None):
        """
        Args:
            table_name: DynamoDB table name. Defaults to DYNAMODB_METADATA_TABLE env var.
        """
        self.table_name = table_name or os.getenv('DYNAMODB_METADATA_TABLE', 'CourseMetadata')
        self.dynamodb = _get_dynamodb_resource()
        self.table = self.dynamodb.Table(self.table_name)

    def get_course_metadata(self, course_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch metadata for a specific course.

        Expected attributes in DynamoDB:
        - course_id (Partition Key)
        - university_id (e.g., 'SFC-university')
        - program_id (e.g., 'bs-computer-science')
        - course_code (e.g., 'cs101')
        - title (Display name)

        Args:
            course_id: The unique course identifier.

        Returns:
            Dictionary of metadata or None if not found.
        """
        try:
            response = self.table.get_item(Key={'course_id': course_id})
            return response.get('Item')
        except Exception as e:
            print(f"[DynamoDB] Error fetching metadata for {course_id}: {str(e)}")
            return None
