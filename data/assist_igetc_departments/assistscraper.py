#!/usr/bin/env python3
"""
ASSIST Text File Parser
Parses copied ASSIST.org content and creates separate JSON files for each department.
What a scrape!!!!!!
"""

import json
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse

class AssistTextParser:
    def __init__(self, output_dir: str = "assist_departments"):
        """
        Initialize the ASSIST text parser.
        
        Args:
            output_dir: Directory to save JSON files
        """
        self.output_dir = output_dir
        self.current_department = None
        self.departments = []
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Column mapping for the standard ASSIST table format
        self.column_headers = [
            "Course", "Title", "Semester Units", "IGETC Areas", 
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
    
    def is_department_header(self, line: str) -> bool:
        """
        Determine if a line is a department header.
        Department headers are typically standalone subject names.
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
            'More information', 'CSU GE Transfer', 'UC IGETC'
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
        
        # If it looks like a department name (letters, spaces, some punctuation)
        if re.match(r'^[A-Za-z\s\-&/()]+$', line) and len(line.split()) <= 5:
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
            continuation_areas, continuation_approved, continuation_removed = self.extract_igetc_areas_from_line_parts(parts)
            
            # If we found IGETC areas or dates, treat as continuation
            if continuation_areas or continuation_approved.get("raw") or continuation_removed.get("raw"):
                continuation_data = {"is_continuation": True}
                
                if continuation_areas:
                    continuation_data["igetc_areas"] = continuation_areas
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
        
        # Extract IGETC areas and dates from remaining parts
        remaining_parts = parts[3:] if len(parts) > 3 else []
        igetc_areas, approved_date, removed_date = self.extract_igetc_areas_from_line_parts(remaining_parts)
        
        # If we didn't find dates in the remaining parts, try to extract from specific positions
        if not approved_date.get("raw") and len(parts) > 4:
            approved_date = self.parse_semester_code(parts[4])
        if not removed_date.get("raw") and len(parts) > 5:
            removed_date = self.parse_semester_code(parts[5])
        
        # Parse units
        units_float = None
        if units:
            units_match = re.search(r'(\d+\.?\d*)', units)
            if units_match:
                units_float = float(units_match.group(1))
        
        # Format IGETC areas with dates and status
        igetc_areas_with_dates = self.format_igetc_areas_with_dates(igetc_areas, approved_date, removed_date)
        
        # Calculate course-level status from IGETC areas
        course_removal_exists = bool(removed_date and removed_date.get("raw"))
        course_is_active = not course_removal_exists or self.is_date_in_future(removed_date)
        
        # If course has multiple IGETC areas, determine overall status
        if igetc_areas_with_dates:
            area_removal_exists = any(area.get("removal_date_exists", False) for area in igetc_areas_with_dates)
            area_is_active = any(area.get("is_active", True) for area in igetc_areas_with_dates)
        else:
            area_removal_exists = course_removal_exists  
            area_is_active = course_is_active

        # Remove course-level date fields entirely - all date info should be in IGETC areas
        course_data = {
            "course_code": course_code,
            "title": title,
            "units": units_float,
            "units_raw": units,
            "igetc_areas": igetc_areas_with_dates,
            "notes": notes,
            "removal_date_exists": area_removal_exists,
            "is_active": area_is_active
        }
        
        return course_data
    
    def parse_file(self, file_path: str) -> List[Dict]:
        """
        Parse the entire ASSIST text file and extract all departments.
        """
        print(f"Parsing file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_dept = None
        departments = []
        current_courses = []
        previous_course = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if this is a department header
            if self.is_department_header(line):
                # Save previous department if it exists
                if current_dept and current_courses:
                    dept_data = {
                        "name": current_dept,
                        "code": self.extract_dept_code(current_dept),
                        "description": f"{current_dept} courses for IGETC transfer",
                        "courses": current_courses.copy(),
                        "total_courses": len(current_courses),
                        "active_courses": len([c for c in current_courses if c.get("is_active", True)]),
                        "removed_courses": len([c for c in current_courses if not c.get("is_active", True)]),
                        "courses_with_removal_dates": len([c for c in current_courses if c.get("removal_date_exists", True)]),
                        "courses_with_future_removal": self.count_courses_with_future_removal(current_courses)
                    }
                    departments.append(dept_data)
                    print(f"Completed department: {current_dept} ({len(current_courses)} courses)")
            
                # Start new department
                current_dept = line
                current_courses = []
                previous_course = None
                continue
            
            # Skip column headers
            if line.startswith('Course\t'):
                continue
            
            # Try to parse as course line
            if current_dept:
                try:
                    course_data = self.parse_course_line(line, previous_course)
                    
                    if course_data:
                        if course_data.get("is_continuation") and previous_course:
                            # Handle IGETC area continuations with individual dates
                            if "igetc_areas" in course_data:
                                # Get the dates for this continuation line
                                continuation_approved = course_data.get("date_approved", {"semester": "", "year": "", "formatted": "", "raw": ""})
                                continuation_removed = course_data.get("date_removed", {"semester": "", "year": "", "formatted": "", "raw": ""})
                                
                                # Merge with existing IGETC areas
                                previous_course["igetc_areas"] = self.merge_igetc_areas_with_dates(
                                    previous_course["igetc_areas"],
                                    course_data["igetc_areas"],
                                    continuation_approved,
                                    continuation_removed
                                )
                                
                                # Update course-level removal status if needed
                                if any(area.get("removal_date_exists", False) for area in previous_course["igetc_areas"]):
                                    previous_course["removal_date_exists"] = True
                                    # Check if any areas are still active
                                    previous_course["is_active"] = any(area.get("is_active", True) for area in previous_course["igetc_areas"])
                            
                            # Handle note continuations
                            if "notes" in course_data:
                                previous_course["notes"].extend(course_data["notes"])
                        else:
                            # New course
                            current_courses.append(course_data)
                            previous_course = course_data
                except Exception as e:
                    print(f"Warning: Error parsing course line in {current_dept}: {e}")
                    print(f"  Problematic line: {line[:100]}...")
                    continue
        
        # Don't forget the last department
        if current_dept and current_courses:
            dept_data = {
                "name": current_dept,
                "code": self.extract_dept_code(current_dept),
                "description": f"{current_dept} courses for IGETC transfer",
                "courses": current_courses.copy(),
                "total_courses": len(current_courses),
                "active_courses": len([c for c in current_courses if c.get("is_active", True)]),
                "removed_courses": len([c for c in current_courses if not c.get("is_active", True)]),
                "courses_with_removal_dates": len([c for c in current_courses if c.get("removal_date_exists", True)]),
                "courses_with_future_removal": self.count_courses_with_future_removal(current_courses)
            }
            departments.append(dept_data)
            print(f"Completed department: {current_dept} ({len(current_courses)} courses)")
        
        print(f"Total departments found: {len(departments)}")
        return departments
    
    def extract_dept_code(self, dept_name: str) -> str:
        """
        Extract department code from department name.
        """
        # Common patterns for department codes
        code_patterns = [
            r'\b([A-Z]{2,6})\b',  # 2-6 uppercase letters
            r'^([A-Z]+)',  # Starting uppercase letters
        ]
        
        for pattern in code_patterns:
            match = re.search(pattern, dept_name.upper())
            if match:
                code = match.group(1)
                # Filter out common words that aren't codes
                if code not in ['AND', 'THE', 'OF', 'IN', 'FOR', 'TO', 'WITH']:
                    return code
        
        # Fallback: use first word
        first_word = dept_name.split()[0] if dept_name.split() else dept_name
        return re.sub(r'[^A-Z]', '', first_word.upper())[:6]
    
    def save_department_json(self, dept_data: Dict) -> str:
        """Save individual department data to JSON file."""
        # Clean department name for filename
        dept_name = dept_data["name"].replace(' ', '_').replace('/', '_').replace('-', '_')
        dept_name = re.sub(r'[^a-zA-Z0-9_]', '', dept_name).lower()
        
        filename = f"SMC_igetc_{dept_name}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Create comprehensive output structure
        output_data = {
            "metadata": {
                "source": "Santa Monica College IGETC Course List",
                "academic_year": "2024-2025",
                "department_name": dept_data["name"],
                "department_code": dept_data["code"],
                "scraped_at": datetime.now().isoformat(),
                "total_courses": dept_data["total_courses"],
                "active_courses": dept_data["active_courses"],
                "removed_courses": dept_data.get("removed_courses", 0),
                "courses_with_removal_dates": dept_data.get("courses_with_removal_dates", 0),
                "data_type": "IGETC_transfer_courses"
            },
            "department": {
                "name": dept_data["name"],
                "code": dept_data["code"],
                "description": dept_data["description"],
                "course_count": dept_data["total_courses"],
                "active_course_count": dept_data["active_courses"],
                "removed_course_count": dept_data.get("removed_courses", 0)
            },
            "courses": dept_data["courses"],
            "summary": {
                "igetc_areas_covered": self.get_igetc_areas_summary(dept_data["courses"]),
                "unit_range": self.get_unit_range(dept_data["courses"]),
                "most_recent_additions": self.get_recent_courses(dept_data["courses"]),
                "removal_status": {
                    "active_courses": dept_data["active_courses"],
                    "removed_courses": dept_data.get("removed_courses", 0),
                    "courses_with_future_removal": dept_data.get("courses_with_future_removal", 0)
                }
            }
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            # Show status summary
            active = dept_data["active_courses"]
            total = dept_data["total_courses"]
            removed = dept_data.get("removed_courses", 0)
            with_removal = dept_data.get("courses_with_removal_dates", 0)
            
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
    
    def get_igetc_areas_summary(self, courses: List[Dict]) -> Dict:
        """Get summary of IGETC areas covered by department with status information."""
        area_counts = {}
        area_status = {}
        
        for course in courses:
            igetc_areas = course.get("igetc_areas", [])
            # Handle both old format (list of strings) and new format (list of dicts)
            for area_data in igetc_areas:
                if isinstance(area_data, dict):
                    area = area_data.get("area", "")
                    is_active = area_data.get("is_active", True)
                    has_removal = area_data.get("removal_date_exists", False)
                else:
                    area = area_data  # Old format compatibility
                    is_active = True
                    has_removal = False
                
                if area:
                    area_counts[area] = area_counts.get(area, 0) + 1
                    
                    # Track status information
                    if area not in area_status:
                        area_status[area] = {"active": 0, "removed": 0, "future_removal": 0}
                    
                    if is_active:
                        if has_removal:
                            area_status[area]["future_removal"] += 1
                        else:
                            area_status[area]["active"] += 1
                    else:
                        area_status[area]["removed"] += 1
        
        return {
            "area_counts": area_counts,
            "area_status": area_status
        }
    
    def get_unit_range(self, courses: List[Dict]) -> Dict:
        """Get unit range for courses in department."""
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
        # Sort by approval year (extract year from IGETC area date_approved)
        courses_with_years = []
        for course in courses:
            igetc_areas = course.get("igetc_areas", [])
            if not igetc_areas:
                continue
                
            # For courses with multiple IGETC areas, use the latest approval date
            # This represents when the course was most recently added/reapproved for IGETC
            approval_years = []
            for area in igetc_areas:
                if isinstance(area, dict):
                    approved = area.get("date_approved", {})
                    year = approved.get("year")
                    if year:
                        approval_years.append(int(year))
            
            if approval_years:
                # Use the latest approval year (most recent addition/reapproval)
                latest_year = max(approval_years)
                courses_with_years.append((course, latest_year))
        
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
    
    def create_master_summary(self, departments: List[Dict]) -> str:
        """Create a master summary file."""
        total_courses = sum(dept["total_courses"] for dept in departments)
        active_courses = sum(dept["active_courses"] for dept in departments)
        removed_courses = sum(dept.get("removed_courses", 0) for dept in departments)
        courses_with_removal = sum(dept.get("courses_with_removal_dates", 0) for dept in departments)
        courses_with_future_removal = sum(dept.get("courses_with_future_removal", 0) for dept in departments)
        
        # Collect all IGETC areas with detailed status
        all_areas = set()
        area_status_summary = {}
        
        for dept in departments:
            for course in dept["courses"]:
                igetc_areas = course.get("igetc_areas", [])
                # Handle both old format (list of strings) and new format (list of dicts)
                for area_data in igetc_areas:
                    if isinstance(area_data, dict):
                        area = area_data.get("area", "")
                        is_active = area_data.get("is_active", True)
                        has_removal = area_data.get("removal_date_exists", False)
                    else:
                        area = area_data  # Old format compatibility
                        is_active = True
                        has_removal = False
                    
                    if area:
                        all_areas.add(area)
                        
                        # Track global status information
                        if area not in area_status_summary:
                            area_status_summary[area] = {"active": 0, "removed": 0, "future_removal": 0}
                        
                        if is_active:
                            if has_removal:
                                area_status_summary[area]["future_removal"] += 1
                            else:
                                area_status_summary[area]["active"] += 1
                        else:
                            area_status_summary[area]["removed"] += 1
        
        summary_data = {
            "metadata": {
                "source": "Santa Monica College IGETC Course List",
                "academic_year": "2024-2025",
                "generated_at": datetime.now().isoformat(),
                "total_departments": len(departments),
                "total_courses": total_courses,
                "active_courses": active_courses,
                "removed_courses": removed_courses,
                "courses_with_removal_dates": courses_with_removal,
                "courses_with_future_removal": courses_with_future_removal
            },
            "departments": [
                {
                    "name": dept["name"],
                    "code": dept["code"],
                    "course_count": dept["total_courses"],
                    "active_courses": dept["active_courses"],
                    "removed_courses": dept.get("removed_courses", 0),
                    "courses_with_removal_dates": dept.get("courses_with_removal_dates", 0),
                    "courses_with_future_removal": dept.get("courses_with_future_removal", 0)
                }
                for dept in departments
            ],
            "igetc_coverage": {
                "areas_covered": sorted(list(all_areas)),
                "total_areas": len(all_areas),
                "area_status_summary": area_status_summary
            },
            "removal_analysis": {
                "total_active_courses": active_courses,
                "total_removed_courses": removed_courses,
                "total_with_future_removal": courses_with_future_removal,
                "departments_with_removed_courses": len([d for d in departments if d.get("removed_courses", 0) > 0])
            },
            "statistics": {
                "departments_by_course_count": sorted(
                    [(dept["name"], dept["total_courses"]) for dept in departments],
                    key=lambda x: x[1], reverse=True
                )[:10],
                "departments_by_active_courses": sorted(
                    [(dept["name"], dept["active_courses"]) for dept in departments],
                    key=lambda x: x[1], reverse=True
                )[:10]
            }
        }
        
        filename = f"SMC_igetc_summary.json"
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
        departments = self.parse_file(file_path)
        
        if not departments:
            print("No departments found in the file.")
            return []
        
        print(f"Found {len(departments)} departments. Creating JSON files...")
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
        
        # Save individual department files
        created_files = []
        
        for i, dept in enumerate(departments, 1):
            print(f"Processing department {i}/{len(departments)}: {dept['name']}")
            filename = self.save_department_json(dept)
            if filename:
                created_files.append(filename)
        
        # Create master summary
        print("Creating summary file...")
        summary_file = self.create_master_summary(departments)
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
    
    def format_igetc_areas_with_dates(self, igetc_areas: List[str], approved_date: Dict, removed_date: Dict) -> List[Dict]:
        """Format IGETC areas with their corresponding approval/removal dates and active status."""
        formatted_areas = []
        for area in igetc_areas:
            # Determine if this area is active
            has_removal_date = bool(removed_date and removed_date.get("raw"))
            is_active = True
            
            if has_removal_date:
                # If there's a removal date, check if it's in the future
                is_active = self.is_date_in_future(removed_date)
            
            formatted_areas.append({
                "area": area,
                "date_approved": approved_date,
                "date_removed": removed_date,
                "removal_date_exists": has_removal_date,
                "is_active": is_active
            })
        return formatted_areas
    
    def merge_igetc_areas_with_dates(self, existing_areas: List[Dict], new_areas: List[str], approved_date: Dict, removed_date: Dict) -> List[Dict]:
        """Merge new IGETC areas with different dates into existing areas."""
        # Convert new areas to the same format with individual active status
        new_formatted_areas = self.format_igetc_areas_with_dates(new_areas, approved_date, removed_date)
        
        # Combine with existing areas
        all_areas = existing_areas + new_formatted_areas
        
        # Remove duplicates while preserving order (in case same area appears with different dates)
        seen = set()
        unique_areas = []
        for area_data in all_areas:
            area_key = (area_data["area"], area_data["date_approved"].get("raw", ""), area_data["date_removed"].get("raw", ""))
            if area_key not in seen:
                seen.add(area_key)
                unique_areas.append(area_data)
        
        return unique_areas
    
    def count_courses_with_future_removal(self, courses: List[Dict]) -> int:
        """Count courses that have removal dates in the future."""
        count = 0
        for course in courses:
            igetc_areas = course.get("igetc_areas", [])
            for area in igetc_areas:
                if isinstance(area, dict):
                    removed_date = area.get("date_removed", {})
                    if removed_date.get("raw") and self.is_date_in_future(removed_date):
                        count += 1
                        break  # Don't count the same course multiple times
        return count

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Parse ASSIST text file and create department JSON files')
    parser.add_argument('input_file', help='Path to the ASSIST text file')
    parser.add_argument('-o', '--output-dir', default='assist_departments', 
                       help='Output directory for JSON files (default: assist_departments)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        return
    
    # Initialize parser
    parser = AssistTextParser(output_dir=args.output_dir)
    
    # Process the file
    print(f"Processing ASSIST data from: {args.input_file}")
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