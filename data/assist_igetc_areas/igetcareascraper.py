#!/usr/bin/env python3
"""
ASSIST Text File Parser - IGETC Area Version
Parses IGETC area-organized ASSIST.org content and creates separate JSON files for each IGETC area.
What a scrape!!!!!!
"""

import json
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse

class AssistTextParser:
    def __init__(self, output_dir: str = "assist_igetc_areas"):
        """
        Initialize the ASSIST text parser for IGETC areas.
        
        Args:
            output_dir: Directory to save JSON files
        """
        self.output_dir = output_dir
        self.current_area = None
        self.areas = []
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Column mapping for the standard ASSIST table format
        self.column_headers = [
            "Course", "Title", "Semester Units", "Other Areas", 
            "Date Approved", "Date Removed"
        ]
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        return text.strip().replace('\t', ' ').replace('\n', ' ').replace('\r', '')
    
    def parse_semester_code(self, date_str: str) -> Dict[str, str]:
        """
        Parse semester codes like 'F2017', 'S2002', 'Su2007', 'W1999'
        """
        if not date_str:
            return {"semester": "", "year": "", "formatted": "", "raw": ""}
        
        date_str = str(date_str).strip()  # Ensure it's a string
        # Match patterns like F2017, S2002, Su2007, W1999
        match = re.match(r'^([FSWU][us]?)(\d{4})$', date_str)
        
        if not match:
            return {"semester": "", "year": "", "formatted": "", "raw": date_str}
            
        sem_code, year = match.groups()
        
        # Map semester codes to full names
        sem_map = {
            'F': 'Fall',
            'S': 'Spring', 
            'Su': 'Summer',
            'W': 'Winter'
        }
        
        semester = sem_map.get(sem_code, sem_code)
        
        return {
            "semester": semester,
            "year": year,
            "formatted": f"{semester} {year}",
            "raw": date_str
        }
    
    def parse_igetc_areas(self, areas_text: str) -> List[str]:
        """Parse IGETC area codes like '5A', '3B', etc."""
        if not areas_text:
            return []
        
        # Split by whitespace and filter valid IGETC patterns
        areas = []
        for area in areas_text.split():
            area = area.strip()
            # Valid IGETC patterns:
            # 1A, 1B, 1C (Written Communication, Critical Thinking, Oral Communication)
            # 2A (Mathematical Concepts)
            # 3A, 3B (Arts and Humanities)
            # 4 (General Social and Behavioral Sciences - covers all sub-areas)
            # 4A-4J (Social and Behavioral Sciences sub-areas)
            # 5A, 5B, 5C (Physical and Biological Sciences)
            # 6A (Languages Other Than English)
            # 7 (Ethnic Studies)
            # 8A, 8B (Additional courses - rare, mostly historical)
            if re.match(r'^(1[ABC]|2A|3[AB]|4[A-J]?|5[ABC]|6A|7|8[AB])$', area):
                areas.append(area)
        
        return areas
    
    def extract_course_notes(self, line: str) -> Tuple[str, List[str]]:
        """
        Extract special notes from course lines like 'Same as:' and 'Formerly'
        Returns cleaned line and list of notes.
        """
        notes = []
        cleaned_line = line
        
        # Extract "Same as:" notes - but preserve any IGETC areas that might be embedded
        same_as_match = re.search(r'Same as:\s*([^\n\r]+)', line)
        if same_as_match:
            same_as_content = same_as_match.group(1).strip()
            
            # Clean the "Same as:" content by removing embedded IGETC area information
            # Extract just the course reference (e.g., "PHILOS 51" from "PHILOS 51\t4H\tF1991")
            parts = same_as_content.split('\t')
            clean_course_ref = parts[0].strip()  # Take only the first part before any tabs
            
            notes.append(f"Same as: {clean_course_ref}")
            # Remove the "Same as:" part but keep the rest for IGETC area extraction
            cleaned_line = re.sub(r'Same as:[^\n\r]*?(?=\t|\s{2,}|$)', '', cleaned_line)
        
        # Extract "Formerly" notes  
        formerly_match = re.search(r'\(Formerly\s+([^)]+)\)', line)
        if formerly_match:
            notes.append(f"Formerly: {formerly_match.group(1).strip()}")
            cleaned_line = re.sub(r'\(Formerly[^)]+\)', '', cleaned_line)
        
        return cleaned_line.strip(), notes
    
    def extract_igetc_areas_from_line_parts(self, parts: List[str]) -> Tuple[List[str], Dict, Dict]:
        """
        Extract IGETC areas and dates from a line that's been split by tabs.
        Returns: (igetc_areas, approved_date, removed_date)
        """
        igetc_areas = []
        approved_date = {"semester": "", "year": "", "formatted": "", "raw": ""}
        removed_date = {"semester": "", "year": "", "formatted": "", "raw": ""}
        
        # Look through all parts for IGETC areas and dates
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
                
            # Check if this part contains an IGETC area
            potential_areas = self.parse_igetc_areas(part)
            if potential_areas:
                igetc_areas.extend(potential_areas)
                continue
            
            # Check if this part is a date
            if re.match(r'^[FSWU][us]?\d{4}$', part):
                parsed_date = self.parse_semester_code(part)
                if not approved_date.get("raw"):
                    approved_date = parsed_date
                elif not removed_date.get("raw"):
                    removed_date = parsed_date
        
        return igetc_areas, approved_date, removed_date
    
    def is_area_header(self, line: str) -> bool:
        """
        Determine if a line is an IGETC area header.
        IGETC area headers follow patterns like:
        - "Area 1 - English Communication"
        - "1A - English Composition"
        - "Area 2 - Mathematical Concepts and Quantitative Reasoning"
        - "2A - Math"
        """
        line = line.strip()
        
        # Skip empty lines, column headers, and metadata
        if not line or line.startswith('Course\t') or line.startswith('Date Generated'):
            return False
        
        # Skip ASSIST header info
        skip_patterns = [
            'ASSIST Logo', 'ASSIST does not take', 'IGETC Course List',
            'Santa Monica College', 'Academic Year', 'IMPORTANT',
            'The Intersegmental', 'The IGETC pattern', 'The following',
            'Limitations', 'Transfer credit may', 'Per UC policy',
            'More information', 'CSU GE Transfer', 'UC IGETC', 'End of List'
        ]
        
        for pattern in skip_patterns:
            if pattern in line:
                return False
        
        # If the line contains course code patterns, it's probably course data
        if re.search(r'\b[A-Z]{2,6}\s+\d{1,3}[A-Z]?\b', line):
            return False
        
        # If it contains tabs, it's probably course data
        if '\t' in line:
            return False
        
        # Check for main area headers: "Area X - [Description]"
        if re.match(r'^Area\s+\d+\s*-\s*.+', line):
            return True
        
        # Check for sub-area headers: "1A - Description", "2A - Description", etc.
        if re.match(r'^[1-8][A-Z]?\s*-\s*.+', line):
            return True
        
        # Check for special area headers like "4 - Social Sciences" or "7 - Ethnic Studies"
        if re.match(r'^[4-8]\s*-\s*.+', line):
            return True
        
        return False
    
    def parse_course_line(self, line: str, previous_course: Optional[Dict] = None) -> Optional[Dict]:
        """
        Parse a single course line. Handle multi-line IGETC areas and notes.
        """
        line = line.strip()
        if not line:
            return None
        
        # Clean the line and extract notes first
        cleaned_line, notes = self.extract_course_notes(line)
        
        # Split by tabs
        parts = cleaned_line.split('\t')
        
        # First, determine if this is a course line or continuation line
        # A course line should have a course code in the first column
        first_part = parts[0].strip() if parts else ""
        is_course_line = bool(first_part and re.match(r'^[A-Z\s]+\d+[A-Z]?$', first_part))
        
        # Handle continuation lines first (they can have 1-4 parts and previous_course exists)
        if previous_course and not is_course_line:
            # Check if this is a continuation line by looking for IGETC areas or dates
            continuation_areas = []
            continuation_approved = {"semester": "", "year": "", "formatted": "", "raw": ""}
            continuation_removed = {"semester": "", "year": "", "formatted": "", "raw": ""}
            
            # Look through parts for IGETC areas and dates
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                    
                # Check if this part contains IGETC areas
                potential_areas = self.parse_igetc_areas(part)
                if potential_areas:
                    continuation_areas.extend(potential_areas)
                    continue
                
                # Check if this part is a date
                if re.match(r'^[FSWU][us]?\d{4}$', part):
                    parsed_date = self.parse_semester_code(part)
                    if not continuation_approved.get("raw"):
                        continuation_approved = parsed_date
                    elif not continuation_removed.get("raw"):
                        continuation_removed = parsed_date
            
            # If we found IGETC areas or dates, treat as continuation
            if continuation_areas or continuation_approved.get("raw") or continuation_removed.get("raw"):
                continuation_data = {"is_continuation": True}
                
                if continuation_areas:
                    continuation_data["other_igetc_areas"] = continuation_areas
                if continuation_approved.get("raw"):
                    continuation_data["date_approved"] = continuation_approved
                if continuation_removed.get("raw"):
                    continuation_data["date_removed"] = continuation_removed
                if notes:
                    continuation_data["notes"] = notes
                
                return continuation_data
            
            # Check for pure note lines (like "Same as:" without embedded areas/dates)
            if notes and len(parts) <= 2 and not any(self.parse_igetc_areas(part) or re.match(r'^[FSWU][us]?\d{4}$', part.strip()) for part in parts):
                return {
                    "is_continuation": True,
                    "notes": notes
                }
        
        # Must be a course line - check if we have enough parts
        if not is_course_line or len(parts) < 2:
            return None
        
        course_code = self.clean_text(parts[0])
        title = self.clean_text(parts[1])
        units = self.clean_text(parts[2]) if len(parts) > 2 else ""
        
        # Extract other IGETC areas from column 3 (Other Areas)
        other_areas_text = self.clean_text(parts[3]) if len(parts) > 3 else ""
        other_igetc_areas = self.parse_igetc_areas(other_areas_text)
        
        # Extract dates from specific columns
        approved_date = {"semester": "", "year": "", "formatted": "", "raw": ""}
        removed_date = {"semester": "", "year": "", "formatted": "", "raw": ""}
        
        if len(parts) > 4:
            approved_date = self.parse_semester_code(parts[4])
        if len(parts) > 5:
            removed_date = self.parse_semester_code(parts[5])
        
        # Parse units
        units_float = None
        if units:
            units_match = re.search(r'(\d+\.?\d*)', units)
            if units_match:
                units_float = float(units_match.group(1))
        
        # Determine if course is active
        has_removal_date = bool(removed_date and removed_date.get("raw"))
        is_active = True
        if has_removal_date:
            is_active = self.is_date_in_future(removed_date)
        
        course_data = {
            "course_code": course_code,
            "title": title,
            "units": units_float,
            "units_raw": units,
            "date_approved": approved_date,
            "date_removed": removed_date,
            "other_igetc_areas": other_igetc_areas,
            "notes": notes,
            "removal_date_exists": has_removal_date,
            "is_active": is_active
        }
        
        return course_data
    
    def parse_file(self, file_path: str) -> List[Dict]:
        """
        Parse the entire ASSIST text file and extract all IGETC areas.
        """
        print(f"Parsing file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_area = None
        areas = []
        current_courses = []
        previous_course = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if this is an area header
            if self.is_area_header(line):
                # Save previous area if it exists
                if current_area and current_courses:
                    area_data = {
                        "name": current_area,
                        "code": self.extract_area_code(current_area),
                        "description": f"{current_area} courses for IGETC transfer",
                        "courses": current_courses.copy(),
                        "total_courses": len(current_courses),
                        "active_courses": len([c for c in current_courses if c.get("is_active", True)]),
                        "removed_courses": len([c for c in current_courses if not c.get("is_active", True)]),
                        "courses_with_removal_dates": len([c for c in current_courses if c.get("removal_date_exists", True)]),
                        "courses_with_future_removal": self.count_courses_with_future_removal(current_courses)
                    }
                    areas.append(area_data)
                    print(f"Completed area: {current_area} ({len(current_courses)} courses)")
            
                # Start new area
                current_area = line
                current_courses = []
                previous_course = None
                continue
            
            # Skip column headers
            if line.startswith('Course\t'):
                continue
            
            # Try to parse as course line
            if current_area:
                try:
                    course_data = self.parse_course_line(line, previous_course)
                    
                    if course_data:
                        if course_data.get("is_continuation") and previous_course:
                            # Handle other IGETC area continuations
                            if "other_igetc_areas" in course_data:
                                # Merge with existing other IGETC areas (simple list)
                                existing_areas = previous_course.get("other_igetc_areas", [])
                                new_areas = course_data["other_igetc_areas"]
                                previous_course["other_igetc_areas"] = existing_areas + new_areas
                            
                            # Handle date updates from continuation lines
                            if "date_approved" in course_data and course_data["date_approved"].get("raw"):
                                if not previous_course.get("date_approved", {}).get("raw"):
                                    previous_course["date_approved"] = course_data["date_approved"]
                            
                            if "date_removed" in course_data and course_data["date_removed"].get("raw"):
                                if not previous_course.get("date_removed", {}).get("raw"):
                                    previous_course["date_removed"] = course_data["date_removed"]
                                    # Update removal status
                                    previous_course["removal_date_exists"] = True
                                    previous_course["is_active"] = self.is_date_in_future(course_data["date_removed"])
                            
                            # Handle note continuations
                            if "notes" in course_data:
                                previous_course["notes"].extend(course_data["notes"])
                        else:
                            # New course
                            current_courses.append(course_data)
                            previous_course = course_data
                except Exception as e:
                    print(f"Warning: Error parsing course line in {current_area}: {e}")
                    print(f"  Problematic line: {line[:100]}...")
                    continue
        
        # Don't forget the last area
        if current_area and current_courses:
            area_data = {
                "name": current_area,
                "code": self.extract_area_code(current_area),
                "description": f"{current_area} courses for IGETC transfer",
                "courses": current_courses.copy(),
                "total_courses": len(current_courses),
                "active_courses": len([c for c in current_courses if c.get("is_active", True)]),
                "removed_courses": len([c for c in current_courses if not c.get("is_active", True)]),
                "courses_with_removal_dates": len([c for c in current_courses if c.get("removal_date_exists", True)]),
                "courses_with_future_removal": self.count_courses_with_future_removal(current_courses)
            }
            areas.append(area_data)
            print(f"Completed area: {current_area} ({len(current_courses)} courses)")
        
        print(f"Total IGETC areas found: {len(areas)}")
        return areas
    
    def extract_area_code(self, area_name: str) -> str:
        """
        Extract IGETC area code from area name.
        """
        # Extract codes like "1A", "2A", "Area 1", etc.
        # First try to match specific patterns like "1A", "2A", "4B", etc.
        match = re.search(r'\b([1-8][A-Z]?)\b', area_name)
        if match:
            return match.group(1)
        
        # Try to match "Area X" patterns
        match = re.search(r'Area\s+(\d+)', area_name)
        if match:
            return f"Area_{match.group(1)}"
        
        # Fallback: use first word or number found
        first_word = area_name.split()[0] if area_name.split() else area_name
        return re.sub(r'[^A-Z0-9]', '', first_word.upper())[:6]
    
    def save_area_json(self, area_data: Dict) -> str:
        """Save individual IGETC area data to JSON file."""
        # Clean area name for filename
        area_name = area_data["name"].replace(' ', '_').replace('/', '_').replace('-', '_')
        area_name = re.sub(r'[^a-zA-Z0-9_]', '', area_name).lower()
        
        filename = f"SMC_igetc_area_{area_name}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Create comprehensive output structure
        output_data = {
            "metadata": {
                "source": "Santa Monica College IGETC Course List by Area",
                "academic_year": "2024-2025",
                "area_name": area_data["name"],
                "area_code": area_data["code"],
                "scraped_at": datetime.now().isoformat(),
                "total_courses": area_data["total_courses"],
                "active_courses": area_data["active_courses"],
                "removed_courses": area_data.get("removed_courses", 0),
                "courses_with_removal_dates": area_data.get("courses_with_removal_dates", 0),
                "data_type": "IGETC_transfer_courses_by_area"
            },
            "area": {
                "name": area_data["name"],
                "code": area_data["code"],
                "description": area_data["description"],
                "course_count": area_data["total_courses"],
                "active_course_count": area_data["active_courses"],
                "removed_course_count": area_data.get("removed_courses", 0)
            },
            "courses": area_data["courses"],
            "summary": {
                "departments_represented": self.get_departments_summary(area_data["courses"]),
                "unit_range": self.get_unit_range(area_data["courses"]),
                "most_recent_additions": self.get_recent_courses(area_data["courses"]),
                "removal_status": {
                    "active_courses": area_data["active_courses"],
                    "removed_courses": area_data.get("removed_courses", 0),
                    "courses_with_future_removal": area_data.get("courses_with_future_removal", 0)
                }
            }
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            # Show status summary
            active = area_data["active_courses"]
            total = area_data["total_courses"]
            removed = area_data.get("removed_courses", 0)
            with_removal = area_data.get("courses_with_removal_dates", 0)
            
            status_msg = f"✓ Saved: {filename} ({total} total, {active} active"
            if removed > 0:
                status_msg += f", {removed} removed"
            if with_removal - removed > 0:
                status_msg += f", {with_removal - removed} future removal"
            status_msg += ")"
            
            print(status_msg)
            return filename
        except Exception as e:
            print(f"✗ Error saving {filename}: {e}")
            print(f"   Attempted path: {filepath}")
            return ""
    
    def get_departments_summary(self, courses: List[Dict]) -> Dict:
        """Get summary of departments represented in this IGETC area."""
        dept_counts = {}
        
        for course in courses:
            course_code = course.get("course_code", "")
            # Extract department prefix from course code (e.g., "MATH" from "MATH 7")
            dept_match = re.match(r'^([A-Z]+)', course_code)
            if dept_match:
                dept = dept_match.group(1)
                dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        return {
            "department_counts": dept_counts,
            "total_departments": len(dept_counts),
            "departments": sorted(dept_counts.keys())
        }
    
    def get_unit_range(self, courses: List[Dict]) -> Dict:
        """Get unit range for courses in area."""
        units = [c.get("units") for c in courses if c.get("units")]
        if not units:
            return {"min": 0, "max": 0, "average": 0}
        
        return {
            "min": min(units),
            "max": max(units),
            "average": round(sum(units) / len(units), 2)
        }
    
    def get_recent_courses(self, courses: List[Dict], limit: int = 5) -> List[Dict]:
        """Get most recently approved courses."""
        # Sort by approval year
        courses_with_years = []
        for course in courses:
            approved_date = course.get("date_approved", {})
            year = approved_date.get("year")
            if year:
                try:
                    approval_year = int(year)
                    courses_with_years.append((course, approval_year))
                except ValueError:
                    continue
        
        # Sort by year descending and take top N
        courses_with_years.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "course_code": course[0]["course_code"],
                "title": course[0]["title"],
                "year_approved": course[1]
            }
            for course in courses_with_years[:limit]
        ]
    
    def create_master_summary(self, areas: List[Dict]) -> str:
        """Create a master summary file."""
        total_courses = sum(area["total_courses"] for area in areas)
        active_courses = sum(area["active_courses"] for area in areas)
        removed_courses = sum(area.get("removed_courses", 0) for area in areas)
        courses_with_removal = sum(area.get("courses_with_removal_dates", 0) for area in areas)
        courses_with_future_removal = sum(area.get("courses_with_future_removal", 0) for area in areas)
        
        # Collect all departments across all areas
        all_departments = set()
        dept_area_mapping = {}
        
        for area in areas:
            area_name = area["name"]
            for course in area["courses"]:
                course_code = course.get("course_code", "")
                # Extract department prefix from course code
                dept_match = re.match(r'^([A-Z]+)', course_code)
                if dept_match:
                    dept = dept_match.group(1)
                    all_departments.add(dept)
                    
                    # Track which areas each department appears in
                    if dept not in dept_area_mapping:
                        dept_area_mapping[dept] = set()
                    dept_area_mapping[dept].add(area_name)
        
        summary_data = {
            "metadata": {
                "source": "Santa Monica College IGETC Course List by Area",
                "academic_year": "2024-2025",
                "generated_at": datetime.now().isoformat(),
                "total_areas": len(areas),
                "total_courses": total_courses,
                "active_courses": active_courses,
                "removed_courses": removed_courses,
                "courses_with_removal_dates": courses_with_removal,
                "courses_with_future_removal": courses_with_future_removal
            },
            "areas": [
                {
                    "name": area["name"],
                    "code": area["code"],
                    "course_count": area["total_courses"],
                    "active_courses": area["active_courses"],
                    "removed_courses": area.get("removed_courses", 0),
                    "courses_with_removal_dates": area.get("courses_with_removal_dates", 0),
                    "courses_with_future_removal": area.get("courses_with_future_removal", 0)
                }
                for area in areas
            ],
            "department_coverage": {
                "departments_represented": sorted(list(all_departments)),
                "total_departments": len(all_departments),
                "department_area_mapping": {dept: sorted(list(areas)) for dept, areas in dept_area_mapping.items()}
            },
            "removal_analysis": {
                "total_active_courses": active_courses,
                "total_removed_courses": removed_courses,
                "total_with_future_removal": courses_with_future_removal,
                "areas_with_removed_courses": len([a for a in areas if a.get("removed_courses", 0) > 0])
            },
            "statistics": {
                "areas_by_course_count": sorted(
                    [(area["name"], area["total_courses"]) for area in areas],
                    key=lambda x: x[1], reverse=True
                ),
                "areas_by_active_courses": sorted(
                    [(area["name"], area["active_courses"]) for area in areas],
                    key=lambda x: x[1], reverse=True
                )
            }
        }
        
        filename = f"SMC_igetc_areas_summary.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Master summary saved: {filename}")
            return filename
        except Exception as e:
            print(f"✗ Error saving summary: {e}")
            return ""
    
    def process_file(self, file_path: str) -> List[str]:
        """
        Main processing function. Parse file and create all JSON outputs.
        """
        # Parse the file
        areas = self.parse_file(file_path)
        
        if not areas:
            print("No IGETC areas found in the file.")
            return []
        
        print(f"Found {len(areas)} IGETC areas. Creating JSON files...")
        print(f"Output directory: {os.path.abspath(self.output_dir)}")
        
        # Verify output directory exists and is writable
        if not os.path.exists(self.output_dir):
            print(f"Creating output directory: {self.output_dir}")
            os.makedirs(self.output_dir, exist_ok=True)
        
        # Test write permissions
        test_file = os.path.join(self.output_dir, "test_write.tmp")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print("✓ Directory is writable")
        except Exception as e:
            print(f"✗ Cannot write to output directory: {e}")
            return []
        
        # Save individual area files
        created_files = []
        
        for i, area in enumerate(areas, 1):
            print(f"Processing area {i}/{len(areas)}: {area['name']}")
            filename = self.save_area_json(area)
            if filename:
                created_files.append(filename)
        
        # Create master summary
        print("Creating summary file...")
        summary_file = self.create_master_summary(areas)
        if summary_file:
            created_files.append(summary_file)
        
        return created_files
    
    def is_date_in_future(self, date_dict: Dict) -> bool:
        """Check if a semester date is in the future relative to current date."""
        if not date_dict or not date_dict.get("raw"):
            return False
        
        # Parse the semester code
        raw_date = date_dict.get("raw", "")
        match = re.match(r'^([FSWU][us]?)(\d{4})$', raw_date)
        if not match:
            return False
        
        sem_code, year_str = match.groups()
        year = int(year_str)
        
        # Get current date (using 2025 as current year based on document date)
        current_year = 2025
        current_month = 6  # June based on document generation date
        
        # Map semester codes to approximate months
        sem_months = {
            'F': 8,   # Fall starts around August
            'S': 1,   # Spring starts around January  
            'Su': 6,  # Summer starts around June
            'W': 12   # Winter starts around December
        }
        
        sem_month = sem_months.get(sem_code, 1)
        
        # Compare dates
        if year > current_year:
            return True
        elif year == current_year:
            return sem_month > current_month
        else:
            return False
    
    def count_courses_with_future_removal(self, courses: List[Dict]) -> int:
        """Count courses that have removal dates in the future."""
        count = 0
        for course in courses:
            removed_date = course.get("date_removed", {})
            if removed_date.get("raw") and self.is_date_in_future(removed_date):
                count += 1
        return count

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Parse ASSIST IGETC area text file and create area JSON files')
    parser.add_argument('input_file', nargs='?', default='igetcbyareadata.txt',
                       help='Path to the ASSIST IGETC area text file (default: igetcbyareadata.txt)')
    parser.add_argument('-o', '--output-dir', default='assist_igetc_areas', 
                       help='Output directory for JSON files (default: assist_igetc_areas)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        return
    
    # Initialize parser
    parser = AssistTextParser(output_dir=args.output_dir)
    
    # Process the file
    print(f"Processing IGETC area data from: {args.input_file}")
    created_files = parser.process_file(args.input_file)
    
    # Summary
    if created_files:
        print(f"\n🎉 Processing complete! Created {len(created_files)} files:")
        for filename in created_files:
            print(f"   📄 {filename}")
        print(f"\nFiles saved in: {args.output_dir}/")
    else:
        print("\n❌ No files were created. Please check your input file format.")

if __name__ == "__main__":
    main() 