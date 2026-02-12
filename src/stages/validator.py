"""
Stage 1: Validation & Inventory

This module validates the IMS-CC structure and builds a content inventory.
"""

from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime

from ..models.migration_report import (
    ValidationReport,
    ContentInventory,
    MigrationError,
    ErrorSeverity
)
from ..config.canvas_schemas import (
    REQUIRED_IMSCC_FILES,
    SYSTEM_XML_FILES,
    CANVAS_PATHS
)
from ..utils.xml_utils import parse_xml_file, find_elements, get_element_attribute
from ..utils.file_utils import (
    validate_file_exists,
    validate_directory_exists,
    find_files_recursive,
    is_xml_file,
    is_html_file,
    is_image_file,
    is_video_file,
    get_file_extension
)


class Validator:
    """
    Stage 1: Validation & Inventory
    
    Validates IMS-CC structure and builds comprehensive content inventory.
    """
    
    def __init__(self, course_directory: Path):
        """
        Initialize validator.
        
        Args:
            course_directory: Path to Canvas course export directory
        """
        self.course_directory = course_directory
        self.manifest_path = course_directory / CANVAS_PATHS['MANIFEST']
        
        self.errors: List[MigrationError] = []
        self.referenced_files: Set[str] = set()
        self.all_files: Set[str] = set()
    
    def validate(self) -> ValidationReport:
        """
        Run complete validation and inventory.
        
        Returns:
            ValidationReport with results
        """
        report = ValidationReport(passed=False, timestamp=datetime.now())
        
        # Step 1: Validate directory structure
        if not self._validate_directory_structure(report):
            return report
        
        # Step 2: Validate manifest file
        if not self._validate_manifest(report):
            return report
        
        # Step 3: Build file inventory
        self._build_file_inventory(report)
        
        # Step 4: Validate file references
        self._validate_file_references(report)
        
        # Step 5: Detect orphaned content
        self._detect_orphaned_content(report)
        
        # Determine if validation passed
        report.passed = len([e for e in self.errors if e.severity == ErrorSeverity.CRITICAL]) == 0
        report.errors = self.errors
        
        return report
    
    def _validate_directory_structure(self, report: ValidationReport) -> bool:
        """
        Validate that the course directory exists and has basic structure.
        
        Args:
            report: ValidationReport to update
            
        Returns:
            True if structure is valid
        """
        # Check if course directory exists
        if not validate_directory_exists(self.course_directory):
            self.errors.append(MigrationError(
                severity=ErrorSeverity.CRITICAL,
                error_type="INVALID_DIRECTORY",
                message=f"Course directory does not exist: {self.course_directory}",
                suggested_action="Verify the path to the Canvas course export directory"
            ))
            return False
        
        # Check for required files
        for required_file in REQUIRED_IMSCC_FILES:
            file_path = self.course_directory / required_file
            if not validate_file_exists(file_path):
                self.errors.append(MigrationError(
                    severity=ErrorSeverity.CRITICAL,
                    error_type="MISSING_REQUIRED_FILE",
                    message=f"Required file not found: {required_file}",
                    file_path=str(file_path),
                    suggested_action="Ensure this is a valid Canvas IMS-CC export"
                ))
                return False
        
        report.imscc_structure_valid = True
        return True
    
    def _validate_manifest(self, report: ValidationReport) -> bool:
        """
        Validate the imsmanifest.xml file.
        
        Args:
            report: ValidationReport to update
            
        Returns:
            True if manifest is valid
        """
        # Check if manifest exists
        if not validate_file_exists(self.manifest_path):
            self.errors.append(MigrationError(
                severity=ErrorSeverity.CRITICAL,
                error_type="MISSING_MANIFEST",
                message="imsmanifest.xml not found",
                file_path=str(self.manifest_path),
                suggested_action="Ensure this is a valid Canvas IMS-CC export"
            ))
            return False
        
        report.manifest_exists = True
        
        # Try to parse manifest
        try:
            root = parse_xml_file(self.manifest_path)
            if root is None:
                raise Exception("Failed to parse manifest")
            
            report.manifest_valid_xml = True
            
            # Basic schema validation (check for required elements)
            if root.tag.endswith('manifest'):
                report.manifest_schema_valid = True
            else:
                self.errors.append(MigrationError(
                    severity=ErrorSeverity.ERROR,
                    error_type="INVALID_MANIFEST_SCHEMA",
                    message="Manifest root element is not 'manifest'",
                    file_path=str(self.manifest_path),
                    suggested_action="Verify this is a valid IMS-CC manifest"
                ))
                return False
            
        except Exception as e:
            self.errors.append(MigrationError(
                severity=ErrorSeverity.CRITICAL,
                error_type="MANIFEST_PARSE_ERROR",
                message=f"Failed to parse manifest: {str(e)}",
                file_path=str(self.manifest_path),
                suggested_action="Check if the XML file is corrupted"
            ))
            return False
        
        return True
    
    def _build_file_inventory(self, report: ValidationReport) -> None:
        """
        Build inventory of all files in the course directory.
        
        Args:
            report: ValidationReport to update
        """
        inventory = ContentInventory()
        
        # Find all files recursively
        all_files = find_files_recursive(
            self.course_directory,
            pattern="*",
            exclude_dirs=["tutor_lms_output", ".git"]
        )
        
        for file_path in all_files:
            relative_path = str(file_path.relative_to(self.course_directory))
            self.all_files.add(relative_path)
            inventory.all_files.append(relative_path)
            
            # Categorize by type
            if is_xml_file(file_path):
                inventory.modules += 1  # Rough estimate
            elif is_html_file(file_path):
                inventory.pages += 1  # Rough estimate
            elif is_image_file(file_path):
                inventory.images += 1
            elif is_video_file(file_path):
                inventory.videos += 1
            elif get_file_extension(file_path) in ('pdf', 'doc', 'docx', 'ppt', 'pptx'):
                inventory.documents += 1
            else:
                inventory.other_files += 1
        
        report.inventory = inventory
    
    def _validate_file_references(self, report: ValidationReport) -> None:
        """
        Validate that all files referenced in manifest exist.
        
        Args:
            report: ValidationReport to update
        """
        try:
            root = parse_xml_file(self.manifest_path)
            if root is None:
                return
            
            # Find all resource elements
            # Try with namespace first
            resources = find_elements(root, './/resource', {})
            
            # If not found, try without namespace
            if not resources:
                resources = root.findall('.//resource')
            
            for resource in resources:
                href = get_element_attribute(resource, 'href')
                if href:
                    self.referenced_files.add(href)
                    report.total_referenced_files += 1
                    
                    # Check if file exists
                    file_path = self.course_directory / href
                    if not validate_file_exists(file_path):
                        report.missing_files += 1
                        report.missing_file_list.append(href)
                        
                        self.errors.append(MigrationError(
                            severity=ErrorSeverity.WARNING,
                            error_type="MISSING_REFERENCED_FILE",
                            message=f"File referenced in manifest not found: {href}",
                            file_path=str(file_path),
                            suggested_action="File may have been deleted or path is incorrect"
                        ))
                
                # Check file elements within resource
                files = resource.findall('.//file')
                for file_elem in files:
                    href = get_element_attribute(file_elem, 'href')
                    if href:
                        self.referenced_files.add(href)
                        report.total_referenced_files += 1
                        
                        file_path = self.course_directory / href
                        if not validate_file_exists(file_path):
                            report.missing_files += 1
                            report.missing_file_list.append(href)
                            
                            self.errors.append(MigrationError(
                                severity=ErrorSeverity.WARNING,
                                error_type="MISSING_REFERENCED_FILE",
                                message=f"File referenced in manifest not found: {href}",
                                file_path=str(file_path),
                                suggested_action="File may have been deleted or path is incorrect"
                            ))
        
        except Exception as e:
            self.errors.append(MigrationError(
                severity=ErrorSeverity.ERROR,
                error_type="REFERENCE_VALIDATION_ERROR",
                message=f"Error validating file references: {str(e)}",
                suggested_action="Check manifest structure"
            ))
    
    def _detect_orphaned_content(self, report: ValidationReport) -> None:
        """
        Detect files that exist but are not referenced in manifest.
        
        Args:
            report: ValidationReport to update
        """
        # Find orphaned files
        orphaned = self.all_files - self.referenced_files
        
        # Filter out system files
        for file_path in orphaned:
            # Skip system files
            file_name = Path(file_path).name
            if file_name in SYSTEM_XML_FILES:
                continue
            
            # Skip output directory
            if 'tutor_lms_output' in file_path:
                continue
            
            report.inventory.orphaned_files.append(file_path)
            
            # Categorize orphaned content
            if is_xml_file(Path(file_path)):
                report.inventory.orphaned_xml_files += 1
            elif is_html_file(Path(file_path)):
                report.inventory.orphaned_html_files += 1
            
            # Log as info (not an error, but worth noting)
            self.errors.append(MigrationError(
                severity=ErrorSeverity.INFO,
                error_type="ORPHANED_CONTENT",
                message=f"File not referenced in manifest: {file_path}",
                file_path=file_path,
                suggested_action="Will attempt intelligent association or place in recovery module"
            ))
        
        # Update referenced files in report
        report.inventory.referenced_files = list(self.referenced_files)
