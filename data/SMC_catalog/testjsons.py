#!/usr/bin/env python3
"""
JSON Structure Validation Script for SMC Catalog Parser Output

This script validates the structural integrity of all parsed JSON files
in the parsed_programs/ directory, ensuring they conform to the expected
schema for program, course, and section data.
"""

import os
import json
import re
import glob
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict


class ValidationError:
    """Represents a single validation error with context."""
    
    def __init__(self, file_path: str, course_code: str, error_type: str, message: str):
        self.file_path = file_path
        self.course_code = course_code
        self.error_type = error_type
        self.message = message
    
    def __str__(self):
        return f"{self.file_path} [{self.course_code}] {self.error_type}: {self.message}"


class JSONValidator:
    """Validates JSON structure for SMC catalog parser output."""
    
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.files_processed = 0
        self.courses_checked = 0
        
        # Excluded files as specified
        self.excluded_files = {
            'independent_studies.json',
            'cross_references.json', 
            'noncredit_classes.json'
        }
        
        # Regex patterns for validation
        self.patterns = {
            'course_code': re.compile(r'^[A-Z]{2,}\s*\d+[A-Z]?$'),
            'units': re.compile(r'^\d+(\.\d+)?\s*UNIT(S)?$'),
            'time_standard': re.compile(r'^\d{1,2}:\d{2}[ap]\.m\.-\d{1,2}:\d{2}[ap]\.m\.$'),
            'time_arrange': re.compile(r'^Arrange-[\d.]+\s*Hours?$'),
            'days': re.compile(r'^[MTWRFSUN]+$|^N$'),  # Standard day codes or 'N' for arrange
        }
    
    def add_error(self, file_path: str, course_code: str, error_type: str, message: str):
        """Add a validation error to the collection."""
        error = ValidationError(file_path, course_code, error_type, message)
        self.errors.append(error)
    
    def validate_required_key(self, data: Dict, key: str, expected_type: type, 
                            file_path: str, course_code: str, context: str = "") -> bool:
        """Validate that a required key exists and has the correct type."""
        context_str = f" in {context}" if context else ""
        
        if key not in data:
            self.add_error(file_path, course_code, "MISSING_KEY", 
                         f"Missing required key '{key}'{context_str}")
            return False
        
        if not isinstance(data[key], expected_type):
            actual_type = type(data[key]).__name__
            expected_type_name = expected_type.__name__
            self.add_error(file_path, course_code, "WRONG_TYPE", 
                         f"Key '{key}'{context_str} has type {actual_type}, expected {expected_type_name}")
            return False
        
        return True
    
    def validate_optional_key(self, data: Dict, key: str, expected_type: type,
                            file_path: str, course_code: str, context: str = "") -> bool:
        """Validate optional key if present."""
        if key not in data:
            return True  # Optional key, absence is OK
        
        # Allow null values for optional keys
        if data[key] is None:
            return True
        
        if not isinstance(data[key], expected_type):
            context_str = f" in {context}" if context else ""
            actual_type = type(data[key]).__name__
            expected_type_name = expected_type.__name__
            self.add_error(file_path, course_code, "WRONG_TYPE", 
                         f"Optional key '{key}'{context_str} has type {actual_type}, expected {expected_type_name}")
            return False
        
        return True
    
    def validate_non_empty_string(self, data: Dict, key: str, file_path: str, 
                                course_code: str, context: str = "") -> bool:
        """Validate that a string field is non-empty."""
        if not self.validate_required_key(data, key, str, file_path, course_code, context):
            return False
        
        if not data[key].strip():
            context_str = f" in {context}" if context else ""
            self.add_error(file_path, course_code, "EMPTY_STRING", 
                         f"Key '{key}'{context_str} is empty or whitespace-only")
            return False
        
        return True
    
    def validate_pattern(self, value: str, pattern_name: str, file_path: str, 
                        course_code: str, field_name: str, context: str = "") -> bool:
        """Validate that a string matches a regex pattern."""
        pattern = self.patterns.get(pattern_name)
        if not pattern:
            raise ValueError(f"Unknown pattern: {pattern_name}")
        
        if not pattern.match(value):
            context_str = f" in {context}" if context else ""
            self.add_error(file_path, course_code, "PATTERN_MISMATCH", 
                         f"Field '{field_name}'{context_str} value '{value}' doesn't match expected pattern")
            return False
        
        return True
    
    def validate_no_extra_keys(self, data: Dict, allowed_keys: set, file_path: str,
                              course_code: str, context: str = "") -> bool:
        """Validate that no unexpected keys are present."""
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            context_str = f" in {context}" if context else ""
            self.add_error(file_path, course_code, "EXTRA_KEYS", 
                         f"Unexpected keys{context_str}: {', '.join(sorted(extra_keys))}")
            return False
        return True
    
    def validate_top_level_structure(self, data: Dict, file_path: str) -> bool:
        """Validate the top-level program structure."""
        course_code = "PROGRAM"  # Use for program-level errors
        
        # Required top-level keys
        valid = True
        valid &= self.validate_non_empty_string(data, 'program_name', file_path, course_code)
        valid &= self.validate_required_key(data, 'program_description', str, file_path, course_code)
        valid &= self.validate_required_key(data, 'courses', list, file_path, course_code)
        
        # Validate courses is non-empty
        if 'courses' in data and isinstance(data['courses'], list):
            if len(data['courses']) == 0:
                self.add_error(file_path, course_code, "EMPTY_LIST", "Courses list is empty")
                valid = False
        
        # Check for unexpected top-level keys
        allowed_top_keys = {'program_name', 'program_description', 'courses'}
        valid &= self.validate_no_extra_keys(data, allowed_top_keys, file_path, course_code)
        
        return valid
    
    def validate_course_structure(self, course: Dict, file_path: str) -> bool:
        """Validate an individual course structure."""
        # Get course_code for error reporting, with fallback
        course_code = course.get('course_code', 'UNKNOWN_COURSE')
        
        valid = True
        
        # Required course keys
        if self.validate_non_empty_string(course, 'course_code', file_path, course_code):
            # Validate course code pattern
            valid &= self.validate_pattern(course['course_code'], 'course_code', 
                                         file_path, course_code, 'course_code')
        else:
            valid = False
        
        valid &= self.validate_non_empty_string(course, 'course_title', file_path, course_code)
        
        if self.validate_required_key(course, 'units', str, file_path, course_code):
            valid &= self.validate_pattern(course['units'], 'units', 
                                         file_path, course_code, 'units')
        else:
            valid = False
        
        valid &= self.validate_required_key(course, 'transfer_info', list, file_path, course_code)
        valid &= self.validate_non_empty_string(course, 'description', file_path, course_code)
        
        if self.validate_required_key(course, 'sections', list, file_path, course_code):
            if len(course['sections']) == 0:
                self.add_error(file_path, course_code, "EMPTY_LIST", "Sections list is empty")
                valid = False
        else:
            valid = False
        
        # Validate transfer_info contains only strings
        if 'transfer_info' in course and isinstance(course['transfer_info'], list):
            for i, item in enumerate(course['transfer_info']):
                if not isinstance(item, str):
                    self.add_error(file_path, course_code, "WRONG_TYPE", 
                                 f"transfer_info[{i}] has type {type(item).__name__}, expected str")
                    valid = False
        
        # Optional course keys
        valid &= self.validate_optional_key(course, 'c_id', str, file_path, course_code)
        valid &= self.validate_optional_key(course, 'cal_getc_area', str, file_path, course_code)
        valid &= self.validate_optional_key(course, 'prerequisites', str, file_path, course_code)
        valid &= self.validate_optional_key(course, 'prerequisite_notes', str, file_path, course_code)
        valid &= self.validate_optional_key(course, 'corequisites', str, file_path, course_code)
        valid &= self.validate_optional_key(course, 'advisory', str, file_path, course_code)
        valid &= self.validate_optional_key(course, 'advisory_notes', str, file_path, course_code)
        valid &= self.validate_optional_key(course, 'formerly', str, file_path, course_code)
        valid &= self.validate_optional_key(course, 'same_as', str, file_path, course_code)
        valid &= self.validate_optional_key(course, 'special_notes', list, file_path, course_code)
        
        # Validate special_notes contains only strings if present
        if 'special_notes' in course and course['special_notes'] is not None:
            if isinstance(course['special_notes'], list):
                for i, note in enumerate(course['special_notes']):
                    if not isinstance(note, str):
                        self.add_error(file_path, course_code, "WRONG_TYPE", 
                                     f"special_notes[{i}] has type {type(note).__name__}, expected str")
                        valid = False
        
        # Check for unexpected course keys
        allowed_course_keys = {
            'course_code', 'course_title', 'units', 'transfer_info', 'description', 'sections',
            'c_id', 'cal_getc_area', 'prerequisites', 'prerequisite_notes', 'corequisites',
            'advisory', 'advisory_notes', 'formerly', 'same_as', 'special_notes'
        }
        valid &= self.validate_no_extra_keys(course, allowed_course_keys, file_path, course_code)
        
        return valid
    
    def validate_section_structure(self, section: Dict, file_path: str, course_code: str) -> bool:
        """Validate an individual section structure."""
        valid = True
        
        # Required section keys
        valid &= self.validate_required_key(section, 'section_number', (str, int), 
                                          file_path, course_code, "section")
        
        if self.validate_required_key(section, 'schedule', list, file_path, course_code, "section"):
            if len(section['schedule']) == 0:
                self.add_error(file_path, course_code, "EMPTY_LIST", 
                             "Section schedule list is empty")
                valid = False
        else:
            valid = False
        
        valid &= self.validate_required_key(section, 'notes', list, file_path, course_code, "section")
        
        # Validate notes contains only strings
        if 'notes' in section and isinstance(section['notes'], list):
            for i, note in enumerate(section['notes']):
                if not isinstance(note, str):
                    self.add_error(file_path, course_code, "WRONG_TYPE", 
                                 f"section notes[{i}] has type {type(note).__name__}, expected str")
                    valid = False
        
        # Modality is required and must be non-empty
        if self.validate_required_key(section, 'modality', str, file_path, course_code, "section"):
            if not section['modality'] or not section['modality'].strip():
                self.add_error(file_path, course_code, "EMPTY_STRING", 
                             "Section modality is empty or whitespace-only")
                valid = False
        else:
            valid = False
        
        # Optional section keys
        valid &= self.validate_optional_key(section, 'duration', str, file_path, course_code, "section")
        valid &= self.validate_optional_key(section, 'co_enrollment_with', str, file_path, course_code, "section")
        
        # Check for unexpected section keys
        allowed_section_keys = {
            'section_number', 'schedule', 'notes', 'modality', 'duration', 'co_enrollment_with'
        }
        valid &= self.validate_no_extra_keys(section, allowed_section_keys, file_path, course_code, "section")
        
        return valid
    
    def validate_schedule_entry(self, schedule_entry: Dict, file_path: str, course_code: str) -> bool:
        """Validate an individual schedule entry."""
        valid = True
        
        # Required schedule keys
        valid &= self.validate_required_key(schedule_entry, 'time', str, 
                                          file_path, course_code, "schedule")
        valid &= self.validate_required_key(schedule_entry, 'days', str, 
                                          file_path, course_code, "schedule")
        valid &= self.validate_non_empty_string(schedule_entry, 'location', 
                                              file_path, course_code, "schedule")
        valid &= self.validate_non_empty_string(schedule_entry, 'instructor', 
                                              file_path, course_code, "schedule")
        
        # Validate time pattern
        if 'time' in schedule_entry and isinstance(schedule_entry['time'], str):
            time_value = schedule_entry['time']
            time_valid = (self.patterns['time_standard'].match(time_value) or 
                         self.patterns['time_arrange'].match(time_value))
            if not time_valid:
                self.add_error(file_path, course_code, "PATTERN_MISMATCH", 
                             f"Schedule time '{time_value}' doesn't match expected pattern")
                valid = False
        
        # Validate days pattern
        if 'days' in schedule_entry and isinstance(schedule_entry['days'], str):
            days_value = schedule_entry['days']
            if not self.patterns['days'].match(days_value):
                self.add_error(file_path, course_code, "PATTERN_MISMATCH", 
                             f"Schedule days '{days_value}' doesn't match expected pattern")
                valid = False
        
        # Check for unexpected schedule keys
        allowed_schedule_keys = {'time', 'days', 'location', 'instructor'}
        valid &= self.validate_no_extra_keys(schedule_entry, allowed_schedule_keys, 
                                           file_path, course_code, "schedule")
        
        return valid
    
    def validate_file(self, file_path: str) -> bool:
        """Validate a single JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.add_error(file_path, "FILE", "JSON_ERROR", f"Invalid JSON: {e}")
            return False
        except Exception as e:
            self.add_error(file_path, "FILE", "READ_ERROR", f"Could not read file: {e}")
            return False
        
        self.files_processed += 1
        
        # Validate top-level structure
        if not self.validate_top_level_structure(data, file_path):
            return False
        
        # Validate each course
        if 'courses' not in data or not isinstance(data['courses'], list):
            return False
        
        file_valid = True
        for course in data['courses']:
            if not isinstance(course, dict):
                self.add_error(file_path, "UNKNOWN_COURSE", "WRONG_TYPE", 
                             "Course entry is not a dictionary")
                file_valid = False
                continue
            
            self.courses_checked += 1
            course_valid = self.validate_course_structure(course, file_path)
            
            # Validate sections if course structure is valid
            if course_valid and 'sections' in course and isinstance(course['sections'], list):
                course_code = course.get('course_code', 'UNKNOWN_COURSE')
                
                for section in course['sections']:
                    if not isinstance(section, dict):
                        self.add_error(file_path, course_code, "WRONG_TYPE", 
                                     "Section entry is not a dictionary")
                        course_valid = False
                        continue
                    
                    section_valid = self.validate_section_structure(section, file_path, course_code)
                    
                    # Validate schedule entries if section structure is valid
                    if section_valid and 'schedule' in section and isinstance(section['schedule'], list):
                        for schedule_entry in section['schedule']:
                            if not isinstance(schedule_entry, dict):
                                self.add_error(file_path, course_code, "WRONG_TYPE", 
                                             "Schedule entry is not a dictionary")
                                section_valid = False
                                continue
                            
                            if not self.validate_schedule_entry(schedule_entry, file_path, course_code):
                                section_valid = False
                    
                    if not section_valid:
                        course_valid = False
            
            if not course_valid:
                file_valid = False
        
        return file_valid
    
    def get_json_files(self, directory: str) -> List[str]:
        """Get all JSON files in directory, excluding specified files."""
        all_files = glob.glob(os.path.join(directory, "*.json"))
        filtered_files = []
        
        for file_path in all_files:
            filename = os.path.basename(file_path)
            if filename not in self.excluded_files:
                filtered_files.append(file_path)
        
        return sorted(filtered_files)
    
    def print_summary(self):
        """Print validation summary and statistics."""
        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Files processed: {self.files_processed}")
        print(f"Courses checked: {self.courses_checked}")
        print(f"Total errors found: {len(self.errors)}")
        
        if self.errors:
            print(f"\n{'='*60}")
            print("ERRORS BY FILE")
            print(f"{'='*60}")
            
            # Group errors by file
            errors_by_file = defaultdict(list)
            for error in self.errors:
                errors_by_file[error.file_path].append(error)
            
            for file_path in sorted(errors_by_file.keys()):
                file_errors = errors_by_file[file_path]
                filename = os.path.basename(file_path)
                print(f"\n{filename} ({len(file_errors)} errors):")
                
                # Group by course code within file
                errors_by_course = defaultdict(list)
                for error in file_errors:
                    errors_by_course[error.course_code].append(error)
                
                for course_code in sorted(errors_by_course.keys()):
                    course_errors = errors_by_course[course_code]
                    print(f"  [{course_code}] ({len(course_errors)} errors):")
                    for error in course_errors:
                        print(f"    {error.error_type}: {error.message}")
        else:
            print("\n✅ All files passed validation!")
    
    def run_validation(self, directory: str = "data/SMC_catalog/parsed_programs") -> int:
        """Run validation on all JSON files in the directory."""
        if not os.path.exists(directory):
            print(f"Error: Directory '{directory}' does not exist")
            return 1
        
        json_files = self.get_json_files(directory)
        
        if not json_files:
            print(f"No JSON files found in '{directory}' (excluding exceptions)")
            return 1
        
        print(f"Validating {len(json_files)} JSON files...")
        print(f"Excluded files: {', '.join(sorted(self.excluded_files))}")
        
        for file_path in json_files:
            filename = os.path.basename(file_path)
            print(f"  Validating {filename}...", end="", flush=True)
            
            if self.validate_file(file_path):
                print(" ✅")
            else:
                print(" ❌")
        
        self.print_summary()
        
        # Return non-zero exit code if errors were found
        return 1 if self.errors else 0


def main():
    """Main entry point."""
    validator = JSONValidator()
    exit_code = validator.run_validation()
    exit(exit_code)


if __name__ == "__main__":
    main() 