"""
File operation utilities with validation and safety checks.

This module provides safe file operations for the migration pipeline.
"""

import hashlib
import shutil
from pathlib import Path
from typing import Optional, List, Tuple


def validate_file_exists(file_path: Path) -> bool:
    """
    Check if a file exists and is actually a file (not a directory).
    
    Args:
        file_path: Path to check
        
    Returns:
        True if file exists and is a file
    """
    return file_path.exists() and file_path.is_file()


def validate_directory_exists(dir_path: Path) -> bool:
    """
    Check if a directory exists and is actually a directory.
    
    Args:
        dir_path: Path to check
        
    Returns:
        True if directory exists and is a directory
    """
    return dir_path.exists() and dir_path.is_dir()


def ensure_directory_exists(dir_path: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        dir_path: Directory path to ensure exists
    """
    dir_path.mkdir(parents=True, exist_ok=True)


def copy_file_safe(
    source: Path,
    destination: Path,
    overwrite: bool = False
) -> bool:
    """
    Safely copy a file with validation.
    
    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing file
        
    Returns:
        True if copy succeeded, False otherwise
    """
    # Validate source exists
    if not validate_file_exists(source):
        return False
    
    # Check if destination exists
    if destination.exists() and not overwrite:
        return False
    
    # Ensure destination directory exists
    ensure_directory_exists(destination.parent)
    
    try:
        shutil.copy2(source, destination)
        return True
    except Exception:
        return False


def get_file_hash(file_path: Path, algorithm: str = 'sha256') -> Optional[str]:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        Hex digest of file hash or None if file doesn't exist
    """
    if not validate_file_exists(file_path):
        return None
    
    hash_obj = hashlib.new(algorithm)
    
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception:
        return None


def get_content_hash(content: str, algorithm: str = 'sha256') -> str:
    """
    Calculate hash of string content.
    
    Args:
        content: String content
        algorithm: Hash algorithm
        
    Returns:
        Hex digest of content hash
    """
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(content.encode('utf-8'))
    return hash_obj.hexdigest()


def get_file_size(file_path: Path) -> Optional[int]:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes or None if file doesn't exist
    """
    if not validate_file_exists(file_path):
        return None
    
    return file_path.stat().st_size


def get_file_extension(file_path: Path) -> str:
    """
    Get file extension (lowercase, without dot).
    
    Args:
        file_path: Path to file
        
    Returns:
        File extension (e.g., 'xml', 'html', 'png')
    """
    return file_path.suffix.lstrip('.').lower()


def is_xml_file(file_path: Path) -> bool:
    """
    Check if file is an XML file based on extension.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file has .xml extension
    """
    return get_file_extension(file_path) == 'xml'


def is_html_file(file_path: Path) -> bool:
    """
    Check if file is an HTML file based on extension.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file has .html or .htm extension
    """
    ext = get_file_extension(file_path)
    return ext in ('html', 'htm')


def is_image_file(file_path: Path) -> bool:
    """
    Check if file is an image based on extension.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file has image extension
    """
    ext = get_file_extension(file_path)
    return ext in ('jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp')


def is_video_file(file_path: Path) -> bool:
    """
    Check if file is a video based on extension.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file has video extension
    """
    ext = get_file_extension(file_path)
    return ext in ('mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv')


def find_files_recursive(
    directory: Path,
    pattern: str = "*",
    exclude_dirs: Optional[List[str]] = None
) -> List[Path]:
    """
    Recursively find files matching a pattern.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern (e.g., "*.xml")
        exclude_dirs: List of directory names to exclude
        
    Returns:
        List of matching file paths
    """
    if not validate_directory_exists(directory):
        return []
    
    exclude_dirs = exclude_dirs or []
    files = []
    
    for item in directory.rglob(pattern):
        # Skip if in excluded directory
        if any(excluded in item.parts for excluded in exclude_dirs):
            continue
        
        if item.is_file():
            files.append(item)
    
    return files


def get_relative_path(file_path: Path, base_path: Path) -> Path:
    """
    Get relative path from base path to file path.
    
    Args:
        file_path: Target file path
        base_path: Base directory path
        
    Returns:
        Relative path
    """
    try:
        return file_path.relative_to(base_path)
    except ValueError:
        # If file_path is not relative to base_path, return absolute path
        return file_path


def safe_filename(filename: str) -> str:
    """
    Convert a string to a safe filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    # Remove invalid characters
    safe = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    safe = safe.strip('. ')
    
    # Limit length
    if len(safe) > 255:
        name, ext = safe.rsplit('.', 1) if '.' in safe else (safe, '')
        safe = name[:255 - len(ext) - 1] + '.' + ext if ext else name[:255]
    
    return safe


import re  # Add this import at the top
