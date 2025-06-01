#!/usr/bin/env python3
"""
RAG Quality Test Suite

This module provides tools to validate and test the quality of RAG JSON files
generated from ASSIST articulation agreements. It includes:

1. Structure validation - checks for required fields and proper structure
2. Note extraction - extracts and validates course notes
3. Logic block analysis - counts and validates logic blocks
4. Visual comparison helpers - assists with manual verification
"""

import json
import os
import sys
import glob
import argparse
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict


class RAGValidator:
    """Main validator class for RAG JSON files."""
    
    def __init__(self, file_path: Optional[str] = None):
        """Initialize the validator with an optional file path."""
        self.file_path = file_path
        self.data = None
        self.issues = []
        self.stats = {}
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path: str) -> bool:
        """Load a RAG JSON file for validation."""
        self.file_path = file_path
        self.issues = []
        self.stats = {}
        
        try:
            with open(file_path, 'r') as f:
                self.data = json.load(f)
            return True
        except json.JSONDecodeError as e:
            self.issues.append(f"Invalid JSON: {str(e)}")
            return False
        except Exception as e:
            self.issues.append(f"Error loading file: {str(e)}")
            return False
    
    def validate_structure(self) -> List[str]:
        """Validate the structure of the RAG JSON."""
        if not self.data:
            return ["No data loaded"]
        
        self.issues = []
        self.issues.extend(self._validate_metadata())
        self.issues.extend(self._validate_groups())
        
        # Count logic elements
        and_blocks, or_blocks, courses, max_nesting = self._count_logic_elements()
        self.stats = {
            "and_blocks": and_blocks,
            "or_blocks": or_blocks,
            "courses": courses,
            "max_nesting": max_nesting
        }
        
        return self.issues
    
    def _validate_metadata(self) -> List[str]:
        """Validate metadata fields in the RAG JSON."""
        issues = []
        
        # Check required top-level fields
        required_fields = ["major", "from", "to", "catalog_year", "groups"]
        for field in required_fields:
            if field not in self.data:
                issues.append(f"Missing required field: {field}")
        
        return issues
    
    def _validate_groups(self) -> List[str]:
        """Validate the groups structure in the RAG JSON."""
        issues = []
        
        if "groups" not in self.data:
            issues.append("Missing groups field")
            return issues
        
        if not isinstance(self.data["groups"], list):
            issues.append("Groups should be a list")
            return issues
        
        for i, group in enumerate(self.data["groups"]):
            if not isinstance(group, dict):
                issues.append(f"Group {i+1} should be a dictionary")
                continue
            
            # Check required group fields
            required_group_fields = ["group_id", "group_title", "sections"]
            for field in required_group_fields:
                if field not in group:
                    issues.append(f"Group {i+1} missing {field}")
            
            if "sections" not in group:
                continue
            
            if not isinstance(group["sections"], list):
                issues.append(f"Group {i+1} sections should be a list")
                continue
            
            # Validate sections
            for j, section in enumerate(group["sections"]):
                section_issues = self._validate_section(section, f"Group {i+1}, Section {j+1}")
                issues.extend(section_issues)
        
        return issues
    
    def _validate_section(self, section: Dict, location: str) -> List[str]:
        """Validate a section structure."""
        issues = []
        
        if not isinstance(section, dict):
            issues.append(f"{location} should be a dictionary")
            return issues
        
        # Check required section fields
        required_section_fields = ["section_id", "section_title", "section_logic_type"]
        for field in required_section_fields:
            if field not in section:
                issues.append(f"{location} missing {field}")
        
        # Check for UC courses
        if "uc_courses" not in section:
            issues.append(f"{location} missing uc_courses")
        elif not isinstance(section["uc_courses"], list):
            issues.append(f"{location} uc_courses should be a list")
        else:
            # Validate UC courses
            for k, uc_course in enumerate(section["uc_courses"]):
                course_issues = self._validate_uc_course(uc_course, f"{location}, UC Course {k+1}")
                issues.extend(course_issues)
        
        return issues
    
    def _validate_uc_course(self, uc_course: Dict, location: str) -> List[str]:
        """Validate a UC course structure."""
        issues = []
        
        if not isinstance(uc_course, dict):
            issues.append(f"{location} should be a dictionary")
            return issues
        
        # Check required UC course fields
        required_fields = ["uc_course_id", "uc_course_title", "logic_block"]
        for field in required_fields:
            if field not in uc_course:
                issues.append(f"{location} missing {field}")
        
        # Validate logic block
        if "logic_block" in uc_course:
            logic_issues = self._validate_logic_block(uc_course["logic_block"], f"{location} logic_block")
            issues.extend(logic_issues)
        
        return issues
    
    def _validate_logic_block(self, logic_block: Dict, location: str) -> List[str]:
        """Validate a logic block structure."""
        issues = []
        
        if not isinstance(logic_block, dict):
            issues.append(f"{location} should be a dictionary")
            return issues
        
        # Check type
        if "type" not in logic_block:
            issues.append(f"{location} missing type")
        elif logic_block["type"] not in ["AND", "OR"]:
            issues.append(f"{location} has invalid type: {logic_block['type']}")
        
        # Check courses
        if "courses" not in logic_block:
            issues.append(f"{location} missing courses")
            return issues
        
        if not isinstance(logic_block["courses"], list):
            issues.append(f"{location} courses should be a list")
            return issues
        
        # Validate each course or nested logic block
        for i, item in enumerate(logic_block["courses"]):
            if not isinstance(item, dict):
                issues.append(f"{location} item {i+1} should be a dictionary")
                continue
            
            # Check if it's a nested logic block or a course
            if "type" in item and item["type"] == "AND":
                nested_issues = self._validate_logic_block(item, f"{location} item {i+1}")
                issues.extend(nested_issues)
            elif "name" in item:
                # This is a course
                pass
            else:
                issues.append(f"{location} item {i+1} is neither a valid logic block nor a course")
        
        return issues
    
    def _count_logic_elements(self) -> Tuple[int, int, int, int]:
        """Count the number of AND blocks, OR blocks, courses, and max nesting level."""
        and_blocks = 0
        or_blocks = 0
        courses = 0
        max_nesting = 0
        
        def count_recursive(logic_block, nesting_level):
            nonlocal and_blocks, or_blocks, courses, max_nesting
            
            if not isinstance(logic_block, dict):
                return
            
            max_nesting = max(max_nesting, nesting_level)
            
            if "type" in logic_block:
                if logic_block["type"] == "AND":
                    and_blocks += 1
                elif logic_block["type"] == "OR":
                    or_blocks += 1
                
                if "courses" in logic_block and isinstance(logic_block["courses"], list):
                    for item in logic_block["courses"]:
                        if isinstance(item, dict):
                            if "type" in item and item["type"] == "AND":
                                count_recursive(item, nesting_level + 1)
                            elif "name" in item:
                                courses += 1
        
        # Start counting from groups
        if "groups" in self.data and isinstance(self.data["groups"], list):
            for group in self.data["groups"]:
                if isinstance(group, dict) and "sections" in group and isinstance(group["sections"], list):
                    for section in group["sections"]:
                        if isinstance(section, dict) and "uc_courses" in section and isinstance(section["uc_courses"], list):
                            for uc_course in section["uc_courses"]:
                                if isinstance(uc_course, dict) and "logic_block" in uc_course:
                                    count_recursive(uc_course["logic_block"], 1)
        
        return and_blocks, or_blocks, courses, max_nesting
    
    def extract_notes(self) -> Dict[str, List[Dict]]:
        """Extract all course notes from the RAG JSON."""
        if not self.data:
            return {}
        
        uc_courses_with_notes = []
        ccc_courses_with_notes = []
        
        # Process all groups and sections
        if "groups" in self.data and isinstance(self.data["groups"], list):
            for group in self.data["groups"]:
                if isinstance(group, dict) and "sections" in group and isinstance(group["sections"], list):
                    group_name = group.get("group_title", "Unknown Group")
                    for section in group["sections"]:
                        if isinstance(section, dict) and "uc_courses" in section and isinstance(section["uc_courses"], list):
                            section_name = section.get("section_title", "Unknown Section")
                            
                            # Process each UC course
                            for uc_course_entry in section["uc_courses"]:
                                if isinstance(uc_course_entry, dict):
                                    # Check for UC course notes
                                    if "note" in uc_course_entry:
                                        uc_courses_with_notes.append({
                                            "group": group_name,
                                            "section": section_name,
                                            "code": uc_course_entry.get("uc_course_id", ""),
                                            "title": uc_course_entry.get("uc_course_title", ""),
                                            "note": uc_course_entry["note"]
                                        })
                                    
                                    # Process logic block for CCC courses
                                    if "logic_block" in uc_course_entry:
                                        self._extract_ccc_notes(
                                            uc_course_entry["logic_block"], 
                                            group_name, 
                                            section_name,
                                            uc_course_entry.get("uc_course_id", ""),
                                            ccc_courses_with_notes
                                        )
        
        return {
            "uc_courses": uc_courses_with_notes,
            "ccc_courses": ccc_courses_with_notes
        }
    
    def _extract_ccc_notes(self, logic_block: Dict, group_name: str, section_name: str, 
                          uc_course_id: str, ccc_courses_with_notes: List[Dict]) -> None:
        """Extract CCC course notes from a logic block."""
        if not isinstance(logic_block, dict) or "courses" not in logic_block:
            return
        
        for item in logic_block["courses"]:
            if isinstance(item, dict):
                if "type" in item and item["type"] == "AND":
                    self._extract_ccc_notes(item, group_name, section_name, uc_course_id, ccc_courses_with_notes)
                elif "name" in item and "note" in item:
                    ccc_courses_with_notes.append({
                        "group": group_name,
                        "section": section_name,
                        "uc_course": uc_course_id,
                        "code": item.get("course_letters", ""),
                        "title": item.get("title", ""),
                        "note": item["note"]
                    })
    
    def is_valid(self) -> bool:
        """Check if the RAG JSON is valid."""
        return len(self.issues) == 0


class RAGDirectoryValidator:
    """Validates all RAG JSON files in a directory."""
    
    def __init__(self, directory: str):
        """Initialize with the directory to validate."""
        self.directory = directory
        self.results = {}
    
    def validate_all(self) -> Dict[str, Dict]:
        """Validate all RAG JSON files in the directory."""
        self.results = {}
        
        # Find all JSON files in the directory and subdirectories
        pattern = os.path.join(self.directory, "**/*.json")
        json_files = glob.glob(pattern, recursive=True)
        
        for file_path in json_files:
            relative_path = os.path.relpath(file_path, self.directory)
            validator = RAGValidator(file_path)
            validator.validate_structure()
            notes = validator.extract_notes()
            
            self.results[relative_path] = {
                "valid": validator.is_valid(),
                "issues": validator.issues,
                "stats": validator.stats,
                "notes": notes
            }
        
        return self.results
    
    def print_results(self) -> None:
        """Print validation results in a readable format."""
        if not self.results:
            print("No validation results available. Run validate_all() first.")
            return
        
        valid_count = sum(1 for result in self.results.values() if result["valid"])
        total_count = len(self.results)
        
        print(f"\n===== RAG JSON Validation Results =====")
        print(f"Valid files: {valid_count}/{total_count}")
        print(f"Files with issues: {total_count - valid_count}")
        print("=====================================\n")
        
        for file_path, result in self.results.items():
            if not result["valid"]:
                print(f"\n🔴 {file_path}:")
                for issue in result["issues"]:
                    print(f"  - {issue}")
            else:
                print(f"\n🟢 {file_path}:")
            
            if "stats" in result and result["stats"]:
                stats = result["stats"]
                print(f"  Stats:")
                print(f"    - AND blocks: {stats.get('and_blocks', 0)}")
                print(f"    - OR blocks: {stats.get('or_blocks', 0)}")
                print(f"    - Courses: {stats.get('courses', 0)}")
                print(f"    - Max nesting level: {stats.get('max_nesting', 0)}")
            
            if "notes" in result:
                notes = result["notes"]
                uc_notes = notes.get("uc_courses", [])
                ccc_notes = notes.get("ccc_courses", [])
                
                if uc_notes:
                    print(f"  UC Courses with Notes: {len(uc_notes)}")
                    for i, course in enumerate(uc_notes[:3]):  # Show first 3 for brevity
                        print(f"    {i+1}. {course['code']} - Note: {course['note']}")
                    if len(uc_notes) > 3:
                        print(f"    ... and {len(uc_notes) - 3} more")
                
                if ccc_notes:
                    print(f"  CCC Courses with Notes: {len(ccc_notes)}")
                    for i, course in enumerate(ccc_notes[:3]):  # Show first 3 for brevity
                        print(f"    {i+1}. {course['code']} - Note: {course['note']}")
                    if len(ccc_notes) > 3:
                        print(f"    ... and {len(ccc_notes) - 3} more")


class RAGComparator:
    """Compares RAG JSON files to identify patterns and inconsistencies."""
    
    def __init__(self, directory: str):
        """Initialize with the directory containing RAG JSON files."""
        self.directory = directory
        self.files = []
        self.common_courses = defaultdict(list)
    
    def load_files(self) -> List[str]:
        """Load all RAG JSON files in the directory."""
        pattern = os.path.join(self.directory, "**/*.json")
        self.files = glob.glob(pattern, recursive=True)
        return self.files
    
    def find_common_courses(self) -> Dict[str, List[Dict]]:
        """Find courses that appear in multiple majors."""
        self.common_courses = defaultdict(list)
        
        for file_path in self.files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                major_name = data.get("major", os.path.basename(file_path))
                
                # Process all courses in the file
                self._extract_courses(data, major_name, file_path)
                
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
        
        # Filter to only include courses that appear in multiple majors
        return {k: v for k, v in self.common_courses.items() if len(v) > 1}
    
    def _extract_courses(self, data: Dict, major_name: str, file_path: str) -> None:
        """Extract all courses from a RAG JSON file."""
        if "groups" not in data or not isinstance(data["groups"], list):
            return
        
        for group in data["groups"]:
            if not isinstance(group, dict) or "sections" not in group or not isinstance(group["sections"], list):
                continue
            
            for section in group["sections"]:
                if not isinstance(section, dict) or "uc_courses" not in section or not isinstance(section["uc_courses"], list):
                    continue
                
                for uc_course in section["uc_courses"]:
                    if not isinstance(uc_course, dict):
                        continue
                    
                    # Process UC course
                    if "uc_course_id" in uc_course:
                        course_key = f"UC:{uc_course['uc_course_id']}"
                        self.common_courses[course_key].append({
                            "major": major_name,
                            "file": file_path,
                            "title": uc_course.get("uc_course_title", ""),
                            "note": uc_course.get("note", "")
                        })
                    
                    # Process CCC courses in the logic block
                    if "logic_block" in uc_course:
                        self._extract_ccc_courses_from_logic(
                            uc_course["logic_block"], 
                            major_name, 
                            file_path
                        )
    
    def _extract_ccc_courses_from_logic(self, logic_block: Dict, major_name: str, file_path: str) -> None:
        """Extract CCC courses from a logic block."""
        if not isinstance(logic_block, dict) or "courses" not in logic_block:
            return
        
        for item in logic_block["courses"]:
            if not isinstance(item, dict):
                continue
            
            if "type" in item and item["type"] == "AND":
                self._extract_ccc_courses_from_logic(item, major_name, file_path)
            elif "name" in item and "course_letters" in item:
                course_key = f"CCC:{item['course_letters']}"
                self.common_courses[course_key].append({
                    "major": major_name,
                    "file": file_path,
                    "title": item.get("title", ""),
                    "note": item.get("note", "")
                })
    
    def print_common_courses(self, min_occurrences: int = 2) -> None:
        """Print courses that appear in multiple majors."""
        common = {k: v for k, v in self.common_courses.items() if len(v) >= min_occurrences}
        
        if not common:
            print("No common courses found across majors.")
            return
        
        print(f"\n===== Common Courses (appearing in {min_occurrences}+ majors) =====")
        print(f"Found {len(common)} common courses")
        print("=================================================\n")
        
        # Sort by number of occurrences (descending)
        sorted_courses = sorted(common.items(), key=lambda x: len(x[1]), reverse=True)
        
        for course_key, occurrences in sorted_courses:
            print(f"\n{course_key} - Appears in {len(occurrences)} majors:")
            
            # Check for inconsistencies in titles or notes
            titles = set(occ["title"] for occ in occurrences if occ["title"])
            notes = set(occ["note"] for occ in occurrences if occ["note"])
            
            if len(titles) > 1:
                print(f"  ⚠️ Title inconsistencies found:")
                for title in titles:
                    print(f"    - {title}")
            
            if len(notes) > 1:
                print(f"  ⚠️ Note inconsistencies found:")
                for note in notes:
                    print(f"    - {note}")
            
            # List majors where this course appears
            for occ in occurrences:
                print(f"  - {occ['major']}")


def main():
    """Main entry point for the RAG quality test suite."""
    parser = argparse.ArgumentParser(description="RAG JSON Quality Test Suite")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate RAG JSON structure")
    validate_parser.add_argument("path", help="Path to a RAG JSON file or directory")
    
    # Extract notes command
    notes_parser = subparsers.add_parser("notes", help="Extract course notes from RAG JSON")
    notes_parser.add_argument("file", help="Path to a RAG JSON file")
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare courses across multiple RAG JSON files")
    compare_parser.add_argument("directory", help="Directory containing RAG JSON files")
    compare_parser.add_argument("--min", type=int, default=2, help="Minimum occurrences to consider as common")
    
    args = parser.parse_args()
    
    if args.command == "validate":
        path = args.path
        if os.path.isdir(path):
            validator = RAGDirectoryValidator(path)
            validator.validate_all()
            validator.print_results()
        elif os.path.isfile(path):
            validator = RAGValidator(path)
            validator.validate_structure()
            if validator.is_valid():
                print(f"✅ {path} is valid")
                print(f"Stats: {validator.stats}")
            else:
                print(f"❌ {path} has issues:")
                for issue in validator.issues:
                    print(f"  - {issue}")
        else:
            print(f"Error: Path '{path}' does not exist")
            sys.exit(1)
    
    elif args.command == "notes":
        file_path = args.file
        if not os.path.isfile(file_path):
            print(f"Error: File '{file_path}' does not exist")
            sys.exit(1)
        
        validator = RAGValidator(file_path)
        notes = validator.extract_notes()
        
        print(f"\n===== Course Notes in {os.path.basename(file_path)} =====")
        
        uc_notes = notes.get("uc_courses", [])
        if uc_notes:
            print(f"\nUC Courses with Notes ({len(uc_notes)}):")
            for i, course in enumerate(uc_notes):
                print(f"{i+1}. {course['code']} ({course['title']})")
                print(f"   Group: {course['group']}, Section: {course['section']}")
                print(f"   Note: {course['note']}")
                print()
        else:
            print("\nNo UC courses with notes found.")
        
        ccc_notes = notes.get("ccc_courses", [])
        if ccc_notes:
            print(f"\nCCC Courses with Notes ({len(ccc_notes)}):")
            for i, course in enumerate(ccc_notes):
                print(f"{i+1}. {course['code']} ({course['title']})")
                print(f"   Group: {course['group']}, Section: {course['section']}")
                print(f"   Note: {course['note']}")
                print()
        else:
            print("\nNo CCC courses with notes found.")
    
    elif args.command == "compare":
        directory = args.directory
        if not os.path.isdir(directory):
            print(f"Error: Directory '{directory}' does not exist")
            sys.exit(1)
        
        comparator = RAGComparator(directory)
        comparator.load_files()
        comparator.find_common_courses()
        comparator.print_common_courses(min_occurrences=args.min)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 