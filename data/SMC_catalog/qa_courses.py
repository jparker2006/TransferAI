#!/usr/bin/env python3
"""
Quality Assurance script for course data.
Validates course information across all departments.
"""

import json
import os
import re
from collections import defaultdict

class CourseQA:
    def __init__(self):
        self.issues = defaultdict(list)
        self.stats = defaultdict(int)
        
    def load_catalog_text(self):
        """Load the original catalog text for reference checking."""
        with open("SMC_catalog.txt", 'r') as f:
            return f.read()
            
    def load_department_headers(self):
        """Load the department headers for reference."""
        with open("smc_department_headers.json", 'r') as f:
            return json.load(f)
            
    def check_course(self, course, department_file, catalog_text):
        """Check a single course for potential issues."""
        course_id = course.get('course_id', '')
        title = course.get('title', '')
        units = course.get('units', '')
        
        # Check required fields
        if not course_id:
            self.issues[department_file].append(f"Missing course_id in entry: {course}")
        if not title:
            self.issues[department_file].append(f"Missing title for course: {course_id}")
        if not units:
            self.issues[department_file].append(f"Missing units for course: {course_id}")
            
        # Validate course ID format - now includes C1000 series pattern
        if not re.match(r'^[A-Z]{2,}(?:\s[A-Z]+)?\s+(?:\d+[A-Z]?|C100[0-9])$', course_id):
            self.issues[department_file].append(f"Invalid course ID format: {course_id}")
            
        # Validate units format
        if units and not re.match(r'^\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s+UNITS?$', units):
            self.issues[department_file].append(f"Invalid units format: {units} for course {course_id}")
            
        # Check for course existence in catalog
        course_pattern = re.escape(course_id) + r',\s+' + re.escape(title)
        if not re.search(course_pattern, catalog_text, re.IGNORECASE):
            # Try just the course ID if full pattern not found
            if not re.search(re.escape(course_id) + r',', catalog_text):
                self.issues[department_file].append(f"Course not found in catalog: {course_id}")
            
        # Track statistics
        self.stats['total_courses'] += 1
        if units:
            unit_value = float(units.split()[0])
            self.stats['total_units'] += unit_value
            self.stats['courses_with_units'] += 1
            
    def analyze_course_files(self):
        """Analyze all course JSON files in the course_data directory."""
        catalog_text = self.load_catalog_text()
        department_headers = self.load_department_headers()
        
        # Track all course IDs to check for duplicates
        all_course_ids = {}
        
        print("Starting course data analysis...")
        
        for filename in os.listdir('course_data'):
            if not filename.endswith('_courses.json'):
                continue
                
            department_file = filename
            filepath = os.path.join('course_data', filename)
            
            try:
                with open(filepath, 'r') as f:
                    courses = json.load(f)
            except json.JSONDecodeError:
                self.issues[department_file].append("Invalid JSON format")
                continue
                
            if not isinstance(courses, list):
                self.issues[department_file].append("File content is not a list")
                continue
                
            # Check each course
            for course in courses:
                self.check_course(course, department_file, catalog_text)
                
                # Check for duplicate course IDs
                course_id = course.get('course_id')
                if course_id:
                    if course_id in all_course_ids:
                        self.issues['duplicates'].append(
                            f"Duplicate course ID {course_id} in {department_file} "
                            f"and {all_course_ids[course_id]}"
                        )
                    else:
                        all_course_ids[course_id] = department_file
                        
    def print_report(self):
        """Print a comprehensive QA report."""
        print("\n=== Course Data QA Report ===\n")
        
        print("Statistics:")
        print(f"Total courses: {self.stats['total_courses']}")
        print(f"Courses with units: {self.stats['courses_with_units']}")
        print(f"Total units across all courses: {self.stats['total_units']}")
        print(f"Average units per course: {self.stats['total_units'] / self.stats['courses_with_units']:.2f}")
        
        print("\nIssues Found:")
        if not self.issues:
            print("No issues found! 🎉")
        else:
            for department, dept_issues in self.issues.items():
                if dept_issues:
                    print(f"\n{department}:")
                    for issue in dept_issues:
                        print(f"  - {issue}")
                        
        print("\nQA Analysis Complete!")

def main():
    qa = CourseQA()
    qa.analyze_course_files()
    qa.print_report()

if __name__ == "__main__":
    main() 