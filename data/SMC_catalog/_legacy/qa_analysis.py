#!/usr/bin/env python3
"""
Quality Assurance script for SMC catalog parsing results.
Analyzes all parsed course data for completeness, accuracy, and potential issues.
"""

import json
import os
import re
from collections import Counter, defaultdict

def load_all_course_data():
    """Load all parsed course JSON files."""
    course_data_dir = "course_data"
    all_courses = []
    department_stats = {}
    
    if not os.path.exists(course_data_dir):
        print(f"Error: {course_data_dir} directory not found")
        return [], {}
    
    for filename in os.listdir(course_data_dir):
        if filename.endswith('_courses.json'):
            filepath = os.path.join(course_data_dir, filename)
            department_name = filename.replace('_courses.json', '').replace('_', ' ').title()
            
            try:
                with open(filepath, 'r') as f:
                    courses = json.load(f)
                    all_courses.extend(courses)
                    department_stats[department_name] = len(courses)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading {filename}: {e}")
    
    return all_courses, department_stats

def analyze_course_completeness(courses):
    """Analyze completeness of course data."""
    print("=== COURSE COMPLETENESS ANALYSIS ===")
    
    total_courses = len(courses)
    missing_title = 0
    missing_course_id = 0
    missing_units = 0
    empty_title = 0
    empty_course_id = 0
    
    print(f"Total courses parsed: {total_courses}")
    
    for course in courses:
        # Check for missing fields
        if 'title' not in course:
            missing_title += 1
        elif not course['title'] or course['title'].strip() == '':
            empty_title += 1
            
        if 'course_id' not in course:
            missing_course_id += 1
        elif not course['course_id'] or course['course_id'].strip() == '':
            empty_course_id += 1
            
        if 'units' not in course:
            missing_units += 1
        elif course['units'] is None:
            missing_units += 1
    
    print(f"Missing title field: {missing_title}")
    print(f"Empty title field: {empty_title}")
    print(f"Missing course_id field: {missing_course_id}")
    print(f"Empty course_id field: {empty_course_id}")
    print(f"Missing/null units field: {missing_units}")
    print(f"Data completeness: {((total_courses - missing_title - missing_course_id - missing_units) / total_courses * 100):.1f}%")
    
    return {
        'total': total_courses,
        'missing_units': missing_units,
        'complete_entries': total_courses - missing_title - missing_course_id - missing_units
    }

def analyze_course_ids(courses):
    """Analyze course ID patterns and duplicates."""
    print("\n=== COURSE ID ANALYSIS ===")
    
    course_ids = [course['course_id'] for course in courses if course.get('course_id')]
    course_id_counts = Counter(course_ids)
    duplicates = {cid: count for cid, count in course_id_counts.items() if count > 1}
    
    print(f"Unique course IDs: {len(course_id_counts)}")
    print(f"Duplicate course IDs: {len(duplicates)}")
    
    if duplicates:
        print("Duplicated course IDs:")
        for cid, count in duplicates.items():
            print(f"  {cid}: {count} times")
    
    # Analyze course ID patterns
    department_patterns = defaultdict(set)
    for cid in course_ids:
        # Extract department prefix
        match = re.match(r'^([A-Z]{2,}(?:\s[A-Z]+)?)', cid)
        if match:
            dept_prefix = match.group(1)
            # Extract course number
            number_match = re.search(r'\s+([\w.-]+)$', cid)
            if number_match:
                course_number = number_match.group(1)
                department_patterns[dept_prefix].add(course_number)
    
    print(f"\nDepartment prefixes found: {len(department_patterns)}")
    for dept, numbers in sorted(department_patterns.items()):
        print(f"  {dept}: {len(numbers)} courses")

def analyze_units(courses):
    """Analyze unit patterns and potential issues."""
    print("\n=== UNITS ANALYSIS ===")
    
    units_data = [course.get('units') for course in courses]
    units_counts = Counter(units_data)
    
    print("Units distribution:")
    for units, count in sorted(units_counts.items(), key=lambda x: (x[0] is None, x[0])):
        if units is None:
            print(f"  Missing units: {count} courses")
        else:
            print(f"  {units}: {count} courses")
    
    # Check for unusual unit patterns
    unusual_units = []
    for course in courses:
        units = course.get('units')
        if units and not re.match(r'^\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s+UNITS?$', units, re.IGNORECASE):
            unusual_units.append((course['course_id'], units))
    
    if unusual_units:
        print(f"\nUnusual unit formats found: {len(unusual_units)}")
        for cid, units in unusual_units[:10]:  # Show first 10
            print(f"  {cid}: '{units}'")
        if len(unusual_units) > 10:
            print(f"  ... and {len(unusual_units) - 10} more")

def analyze_titles(courses):
    """Analyze course titles for potential issues."""
    print("\n=== TITLE ANALYSIS ===")
    
    title_lengths = [len(course.get('title', '')) for course in courses]
    avg_title_length = sum(title_lengths) / len(title_lengths) if title_lengths else 0
    
    print(f"Average title length: {avg_title_length:.1f} characters")
    print(f"Shortest title: {min(title_lengths)} characters")
    print(f"Longest title: {max(title_lengths)} characters")
    
    # Check for potentially incomplete titles
    short_titles = [(course['course_id'], course['title']) for course in courses 
                   if course.get('title') and len(course['title']) < 20]
    
    if short_titles:
        print(f"\nPotentially incomplete titles (< 20 chars): {len(short_titles)}")
        for cid, title in short_titles[:5]:  # Show first 5
            print(f"  {cid}: '{title}'")
    
    # Check for titles with unusual patterns
    truncated_titles = []
    for course in courses:
        title = course.get('title', '')
        # Look for titles that might be cut off
        if title.endswith(('AND', 'TO', 'OF', 'IN', 'FOR', 'WITH')):
            truncated_titles.append((course['course_id'], title))
    
    if truncated_titles:
        print(f"\nPotentially truncated titles: {len(truncated_titles)}")
        for cid, title in truncated_titles[:5]:  # Show first 5
            print(f"  {cid}: '{title}'")

def sample_courses_by_pattern(courses):
    """Extract sample courses for manual verification."""
    print("\n=== SAMPLE COURSES FOR MANUAL VERIFICATION ===")
    
    samples = {
        "Single-line format": [],
        "Multi-line format": [],
        "Independent Studies": [],
        "High unit courses": [],
        "Fractional units": [],
        "Honors courses": []
    }
    
    for course in courses:
        cid = course.get('course_id', '')
        title = course.get('title', '')
        units = course.get('units', '')
        
        # Single line (short titles)
        if len(samples["Single-line format"]) < 3 and len(title) < 50:
            samples["Single-line format"].append(course)
        
        # Multi-line (long titles)
        if len(samples["Multi-line format"]) < 3 and len(title) > 80:
            samples["Multi-line format"].append(course)
        
        # Independent Studies
        if len(samples["Independent Studies"]) < 3 and "INDEPENDENT STUDIES" in title:
            samples["Independent Studies"].append(course)
        
        # High unit courses
        if len(samples["High unit courses"]) < 3 and units and ("5 UNITS" in units or "6 UNITS" in units):
            samples["High unit courses"].append(course)
        
        # Fractional units
        if len(samples["Fractional units"]) < 3 and units and "." in units:
            samples["Fractional units"].append(course)
        
        # Honors courses (if any)
        if len(samples["Honors courses"]) < 3 and ("HONORS" in title.upper() or "H " in cid):
            samples["Honors courses"].append(course)
    
    for category, course_list in samples.items():
        if course_list:
            print(f"\n{category}:")
            for course in course_list:
                print(f"  {course['course_id']}: {course['title'][:60]}{'...' if len(course['title']) > 60 else ''}")
                print(f"    Units: {course.get('units', 'N/A')}")

def department_coverage_analysis(department_stats):
    """Analyze department coverage."""
    print("\n=== DEPARTMENT COVERAGE ANALYSIS ===")
    
    print(f"Total departments parsed: {len(department_stats)}")
    
    # Sort by course count
    sorted_depts = sorted(department_stats.items(), key=lambda x: x[1], reverse=True)
    
    print("\nDepartments by course count:")
    for dept, count in sorted_depts:
        print(f"  {dept}: {count} courses")
    
    # Identify departments with unusually low counts (potential parsing issues)
    low_count_depts = [(dept, count) for dept, count in sorted_depts if count < 3]
    if low_count_depts:
        print(f"\nDepartments with < 3 courses (potential issues):")
        for dept, count in low_count_depts:
            print(f"  {dept}: {count} courses")

def main():
    """Run comprehensive QA analysis."""
    print("SMC Catalog Parsing - Quality Assurance Analysis")
    print("=" * 50)
    
    # Load all data
    all_courses, department_stats = load_all_course_data()
    
    if not all_courses:
        print("No course data found. Please run parse_catalog.py first.")
        return
    
    # Run all analyses
    completeness_stats = analyze_course_completeness(all_courses)
    analyze_course_ids(all_courses)
    analyze_units(all_courses)
    analyze_titles(all_courses)
    sample_courses_by_pattern(all_courses)
    department_coverage_analysis(department_stats)
    
    # Summary
    print("\n" + "=" * 50)
    print("QA SUMMARY")
    print("=" * 50)
    print(f"Total courses: {completeness_stats['total']}")
    print(f"Complete entries: {completeness_stats['complete_entries']}")
    print(f"Missing units: {completeness_stats['missing_units']}")
    print(f"Success rate: {(completeness_stats['complete_entries'] / completeness_stats['total'] * 100):.1f}%")
    
    if completeness_stats['missing_units'] > 0:
        print(f"\n⚠️  WARNING: {completeness_stats['missing_units']} courses are missing unit information")
    else:
        print("\n✅ All courses have complete data!")

if __name__ == "__main__":
    main() 