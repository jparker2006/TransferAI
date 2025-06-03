#!/usr/bin/env python3
"""
Script to identify courses missing unit information for analysis.
"""

import json
import os

def find_missing_units():
    """Find all courses missing unit information."""
    course_data_dir = "course_data"
    missing_units_courses = []
    
    for filename in os.listdir(course_data_dir):
        if filename.endswith('_courses.json'):
            filepath = os.path.join(course_data_dir, filename)
            department_name = filename.replace('_courses.json', '').replace('_', ' ').title()
            
            with open(filepath, 'r') as f:
                courses = json.load(f)
                
            for course in courses:
                if course.get('units') is None:
                    missing_units_courses.append({
                        'course_id': course['course_id'],
                        'title': course['title'],
                        'department_file': filename
                    })
    
    return missing_units_courses

def main():
    missing_courses = find_missing_units()
    
    print(f"Found {len(missing_courses)} courses missing units:")
    print("=" * 60)
    
    for course in missing_courses:
        print(f"Course: {course['course_id']}")
        print(f"Title: {course['title']}")
        print(f"File: {course['department_file']}")
        print("-" * 40)
    
    # Output course IDs for easy grepping
    print("\nCourse IDs for grep search:")
    course_ids = [course['course_id'] for course in missing_courses]
    print("|".join([f"^{cid}," for cid in course_ids]))

if __name__ == "__main__":
    main() 