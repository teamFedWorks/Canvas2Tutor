from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
from pathlib import Path

from .service import MigrationService
from .middleware import get_api_key, validate_file_upload, HTTP_403_FORBIDDEN
from fastapi import Depends

router = APIRouter(tags=["Migration"])
migration_service = MigrationService()

@router.post("/migrate", dependencies=[Depends(validate_file_upload)])
async def start_migration(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = Depends(get_api_key)
) -> Dict[str, Any]:
    """
    Upload a course shell ZIP and start the migration process.
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")
    
    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    
    # Save the file and start processing in background
    background_tasks.add_task(
        migration_service.process_migration, 
        task_id, 
        file
    )
    
    return {
        "status": "accepted",
        "task_id": task_id,
        "filename": file.filename,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/status/{task_id}")
async def get_status(task_id: str, api_key: str = Depends(get_api_key)) -> Dict[str, Any]:
    """
    Get the current status of a migration task.
    """
    status = migration_service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return status

@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


class S3MigrateRequest(BaseModel):
    s3_key: str = Field(..., description="S3 object key of the Canvas course ZIP, e.g. 'courses/cs101.zip'")
    bucket: Optional[str] = Field(None, description="Override the default S3 bucket (optional)")


@router.post("/migrate-s3")
async def start_migration_from_s3(
    body: S3MigrateRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key)
) -> Dict[str, Any]:
    """
    Trigger a migration by fetching the Canvas course ZIP directly from S3.
    """
    if not body.s3_key.endswith('.zip'):
        raise HTTPException(status_code=400, detail="s3_key must point to a .zip file")

    task_id = str(uuid.uuid4())

    background_tasks.add_task(
        migration_service.process_migration_from_s3,
        task_id,
        body.s3_key,
        body.bucket,
    )

    return {
        "status": "accepted",
        "task_id": task_id,
        "s3_key": body.s3_key,
        "timestamp": datetime.utcnow().isoformat(),
    }


class HierarchicalMigrateRequest(BaseModel):
    course_id: str = Field(..., description="The course ID to look up in DynamoDB")


@router.post("/migrate/hierarchical")
async def start_hierarchical_migration(
    body: HierarchicalMigrateRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key)
) -> Dict[str, Any]:
    """
    Trigger a migration by looking up metadata in DynamoDB and fetching the 
    corresponding ZIP from the hierarchical S3 structure.
    """
    task_id = str(uuid.uuid4())

    background_tasks.add_task(
        migration_service.process_hierarchical_migration,
        task_id,
        body.course_id
    )

    return {
        "status": "accepted",
        "task_id": task_id,
        "course_id": body.course_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
