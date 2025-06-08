import re
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Schedule:
    time: str
    days: str
    location: str
    instructor: str


@dataclass
class Section:
    section_number: str
    schedule: List[Schedule]  # Can have multiple schedule entries
    notes: List[str]
    duration: Optional[str] = None
    modality: Optional[str] = None
    co_enrollment_with: Optional[str] = None  # Section number that must be taken with this one


@dataclass
class Course:
    course_code: str
    course_title: str
    units: str
    transfer_info: List[str]
    c_id: Optional[str] = None
    cal_getc_area: Optional[str] = None
    special_notes: List[str] = None
    prerequisites: Optional[str] = None
    advisory: Optional[str] = None
    formerly: Optional[str] = None
    description: str = ""
    sections: List[Section] = None
    same_as: Optional[str] = None


@dataclass
class Program:
    program_name: str
    program_description: str
    courses: List[Course]


class SMCCatalogParser:
    def __init__(self, text_file_path: str, output_dir: str = "parsed_programs"):
        self.text_file_path = text_file_path
        self.output_dir = output_dir
        self.programs = []
        self.parsing_warnings = []  # Track potential parsing issues
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def add_warning(self, warning: str):
        """Add a parsing warning for later review"""
        self.parsing_warnings.append(warning)
        print(f"WARNING: {warning}")
    
    def is_valid_section_line(self, potential_section_num: str, rest_of_line: str) -> bool:
        """
        Validate that a line that starts with 4 digits is actually a section line
        and not an address or other content.
        """
        # Check if the rest of the line can be parsed as a schedule
        schedule = self.parse_schedule_line(rest_of_line)
        if schedule:
            return True
        
        # Additional validation patterns for section lines
        # Real section lines typically have time patterns, "Arrange", or specific keywords
        section_indicators = [
            r'\d{1,2}:\d{2}[ap]\.m\.',  # Time patterns
            r'Arrange',                  # Arranged schedules
            r'[MTWRFSU]{1,7}\s',        # Day patterns followed by space
            r'ONLINE',                   # Online courses
            r'TBA'                       # To be announced
        ]
        
        for pattern in section_indicators:
            if re.search(pattern, rest_of_line):
                return True
        
        # Check for common false positive patterns (addresses, years, etc.)
        false_positive_patterns = [
            r'^\d{4}\s+[A-Z][a-z]+\s+Street',      # "1660 Stewart Street"
            r'^\d{4}\s+[A-Z][a-z]+\s+Avenue',      # "1234 Main Avenue"
            r'^\d{4}\s+[A-Z][a-z]+\s+Boulevard',   # "1234 Oak Boulevard"
            r'^\d{4}\s+[A-Z][a-z]+\s+Drive',       # "1234 Park Drive"
            r'^\d{4}\s+[A-Z][a-z]+\s+Road',        # "1234 Park Road"
            r'^\d{4}\s+[A-Z][a-z]+\s+Lane',        # "1234 Oak Lane"
            r'^\d{4}\s*-\s*\d{4}',                 # Year ranges like "2020-2024"
            r'^\d{4}\s+to\s+\d{4}',               # "2020 to 2024"
        ]
        
        full_line = potential_section_num + " " + rest_of_line
        for pattern in false_positive_patterns:
            if re.match(pattern, full_line):
                self.add_warning(f"Rejected potential section '{potential_section_num}' - appears to be address/year: '{full_line.strip()}'")
                return False
        
        # If we can't identify it as a schedule line or a clear false positive,
        # be conservative and reject it
        self.add_warning(f"Rejected potential section '{potential_section_num}' - no valid schedule indicators: '{full_line.strip()}'")
        return False
    
    def validate_parsed_sections(self, course: Course) -> List[Section]:
        """
        Post-process validation to remove sections that don't have meaningful content
        """
        valid_sections = []
        
        for section in course.sections:
            # A valid section should have at least one of:
            # 1. Schedule information
            # 2. Meaningful notes
            # 3. Duration or modality information
            
            has_schedule = len(section.schedule) > 0
            has_meaningful_notes = (
                len(section.notes) > 0 and 
                any(len(note.strip()) > 10 for note in section.notes)  # At least one substantial note
            )
            has_additional_info = section.duration or section.modality or section.co_enrollment_with
            
            if has_schedule or has_meaningful_notes or has_additional_info:
                valid_sections.append(section)
            else:
                self.add_warning(
                    f"Removed empty section '{section.section_number}' from {course.course_code} "
                    f"- no schedule, notes, or additional information"
                )
        
        return valid_sections
    
    def fix_hyphenation(self, text: str) -> str:
        """
        Comprehensively fix words that are hyphenated across lines or improperly split.
        This handles both newline-based hyphenation and space-based hyphenation artifacts.
        """
        # First, handle hyphenation across newlines (original pattern)
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Handle hyphenation with spaces (common in parsed text where newlines became spaces)
        # Pattern: word + dash + space + lowercase word (likely continuation)
        # Be careful not to break legitimate hyphenated words or compounds
        text = re.sub(r'(\w+)-\s+([a-z]\w+)', self._fix_hyphen_with_space, text)
        
        # Fix common specific hyphenation patterns that we know are wrong
        hyphenation_fixes = {
            # Entertainment industry terms
            r'enter-\s*tainment': 'entertainment',
            r'entertain-\s*ment': 'entertainment',
            
            # Common academic/technical terms
            r'require-\s*ments': 'requirements',
            r'develop-\s*ment': 'development',
            r'manage-\s*ment': 'management',
            r'achieve-\s*ment': 'achievement',
            r'establish-\s*ment': 'establishment',
            r'environ-\s*ment': 'environment',
            r'govern-\s*ment': 'government',
            r'improve-\s*ment': 'improvement',
            r'involve-\s*ment': 'involvement',
            r'move-\s*ment': 'movement',
            r'place-\s*ment': 'placement',
            r'state-\s*ment': 'statement',
            r'treat-\s*ment': 'treatment',
            
            # Common education/course terms
            r'comple-\s*tion': 'completion',
            r'instruc-\s*tion': 'instruction',
            r'prepara-\s*tion': 'preparation',
            r'applica-\s*tion': 'application',
            r'informa-\s*tion': 'information',
            r'educa-\s*tion': 'education',
            r'organiza-\s*tion': 'organization',
            r'presenta-\s*tion': 'presentation',
            r'demonstra-\s*tion': 'demonstration',
            r'concentra-\s*tion': 'concentration',
            r'investiga-\s*tion': 'investigation',
            
            # Technology/computer terms
            r'compu-\s*ter': 'computer',
            r'tech-\s*nology': 'technology',
            r'program-\s*ming': 'programming',
            r'develop-\s*ing': 'developing',
            r'proces-\s*sing': 'processing',
            
            # Science terms
            r'labora-\s*tory': 'laboratory',
            r'experi-\s*ment': 'experiment',
            r'analy-\s*sis': 'analysis',
            r'synthe-\s*sis': 'synthesis',
            r'hypothe-\s*sis': 'hypothesis',
            
            # Common words
            r'impor-\s*tant': 'important',
            r'differ-\s*ent': 'different',
            r'inter-\s*est': 'interest',
            r'consis-\s*tent': 'consistent',
            r'expe-\s*rience': 'experience',
            r'knowl-\s*edge': 'knowledge',
            r'under-\s*stand': 'understand',
            r'communi-\s*cation': 'communication',
            r'profes-\s*sional': 'professional',
            r'oppor-\s*tunity': 'opportunity',
            r'neces-\s*sary': 'necessary',
            r'particu-\s*lar': 'particular',
            r'success-\s*ful': 'successful',
            r'effec-\s*tive': 'effective',
            r'crea-\s*tive': 'creative',
            r'compre-\s*hensive': 'comprehensive',
            r'cov-\s*ered': 'covered',
            r'discov-\s*ered': 'discovered',
            r'recov-\s*ered': 'recovered',
            r'consid-\s*ered': 'considered',
            r'deliv-\s*ered': 'delivered',
            r'remem-\s*bered': 'remembered',
            r'numb-\s*ered': 'numbered',
            r'advanc-\s*ed': 'advanced',
            r'balanc-\s*ed': 'balanced',
            r'reduc-\s*ed': 'reduced',
            r'produc-\s*ed': 'produced',
            r'introduc-\s*ed': 'introduced',
            
            # Previously handled cases (keep for backward compatibility)
            r'fur-\s*ther': 'further',
            r'col-\s*lege': 'college',
            r'stu-\s*dents': 'students',
        }
        
        # Apply all the specific fixes
        for pattern, replacement in hyphenation_fixes.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Additional cleanup for any remaining obvious hyphenation artifacts
        # Handle cases like "pre- requisite" -> "prerequisite" for common prefixes
        common_prefixes = ['pre', 'pro', 'anti', 'auto', 'co', 're', 'un', 'non', 'over', 'under', 'out', 'up']
        for prefix in common_prefixes:
            # Pattern: prefix + dash + space + word starting with lowercase
            pattern = rf'\b{prefix}-\s+([a-z]\w+)'
            text = re.sub(pattern, rf'{prefix}\1', text, flags=re.IGNORECASE)
        
        return text
    
    def _fix_hyphen_with_space(self, match):
        """
        Helper function to intelligently fix hyphenated words with spaces.
        Only combines if it looks like a legitimate word break, not a compound word.
        """
        first_part = match.group(1)
        second_part = match.group(2)
        
        # Don't combine if the first part is very short (likely a prefix that should stay hyphenated)
        if len(first_part) <= 2:
            return match.group(0)  # Return original
        
        # Don't combine if it looks like a legitimate compound word pattern
        compound_indicators = ['self', 'well', 'high', 'low', 'long', 'short', 'full', 'half', 'multi', 'single', 'double']
        if first_part.lower() in compound_indicators:
            return match.group(0)  # Return original
        
        # Don't combine if the second part starts with a vowel and might be a separate word
        # (this is a heuristic to avoid combining things like "auto- immune" incorrectly)
        if len(second_part) >= 4 and second_part[0] in 'aeiou' and first_part.lower() not in ['pre', 'pro', 'anti']:
            return match.group(0)  # Return original
        
        # Otherwise, combine them
        return first_part + second_part
    
    def parse(self):
        with open(self.text_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix hyphenation issues first
        content = self.fix_hyphenation(content)
        
        # Split by program markers
        program_sections = re.split(r'\n=([^=\n]+)\n', content)
        
        # Process each program
        for i in range(1, len(program_sections), 2):
            program_name = program_sections[i].strip()
            program_content = program_sections[i + 1] if i + 1 < len(program_sections) else ""
            
            if program_content.strip():
                program = self.parse_program(program_name, program_content)
                self.programs.append(program)
                self.save_program_json(program)
    
    def find_course_boundaries(self, lines: List[str]) -> List[Tuple[int, str, str, str]]:
        """Find all course start positions and extract course info"""
        courses = []
        
        # More robust approach: scan line by line looking for course patterns
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for course code pattern at the start of a line
            course_match = re.match(r'^((?:[A-Z]+\s+)?[A-Z]+(?:\s+ST)?\s+[0-9]+[A-Z]?),\s+(.+)', line)
            if course_match:
                course_code = course_match.group(1)
                title_start = course_match.group(2)
                
                # Check if the units are already on this line (single-line case)
                units_match = re.search(r'(\d+\s+UNITS?)(?:\s|$)', title_start)
                if units_match:
                    # Single-line case: course code, title, and units all on one line
                    title_only = title_start[:units_match.start()].strip()
                    units = units_match.group(1)
                    
                    # Additional validation to avoid false positives
                    if (len(title_only.split()) > 15 or
                        title_only.lower().startswith(('this course', 'students will', 'the ', 'a ', 'an ')) or
                        'combined: maximum UC credit' in title_only or
                        re.search(r'\d{4}\s+\d{1,2}:\d{2}[ap]\.m\.', title_only)):
                        self.add_warning(f"Skipping potential false positive: {course_code} - {title_only[:50]}...")
                        i += 1
                        continue
                    
                    courses.append((i, course_code, title_only, units))
                    self.add_warning(f"Found single-line course: {course_code} - {title_only}")
                else:
                    # Multi-line case: look ahead to find where the title ends and units begin
                    full_title_parts = [title_start]
                    j = i + 1
                    units = None
                    
                    # Look at the next few lines to complete the title and find units
                    while j < len(lines) and j < i + 5:  # Look ahead max 5 lines
                        next_line = lines[j].strip()
                        
                        if not next_line:
                            j += 1
                            continue
                        
                        # Check if this line contains the units
                        units_match = re.search(r'(\d+\s+UNITS?)(?:\s|$)', next_line)
                        if units_match:
                            # Extract title part before units (if any) and units
                            before_units = next_line[:units_match.start()].strip()
                            if before_units:
                                full_title_parts.append(before_units)
                            units = units_match.group(1)
                            break
                        
                        # Check if this line starts with something that indicates it's not part of the title
                        # (like "Transfer:", bullet points, course descriptions, etc.)
                        if (next_line.startswith(('Transfer:', 'C-ID:', 'Cal-GETC', '•', 'This course', 'Physics ')) or
                            re.match(r'^\d{4}\s+', next_line) or  # Section numbers
                            next_line.lower().startswith(('formerly', 'please see', 'maximum credit'))):
                            # This indicates the title ended on the previous line
                            break
                        
                        # Add this line to the title
                        full_title_parts.append(next_line)
                        j += 1
                    
                    if units:
                        # Clean up the title
                        full_title = ' '.join(full_title_parts).strip()
                        full_title = re.sub(r'\s+', ' ', full_title)
                        
                        # Additional validation to avoid false positives
                        # Skip if this looks like description text rather than a course header
                        if (len(full_title.split()) > 15 or  # Very long titles are suspicious
                            full_title.lower().startswith(('this course', 'students will', 'the ', 'a ', 'an ')) or
                            'combined: maximum UC credit' in full_title or
                            re.search(r'\d{4}\s+\d{1,2}:\d{2}[ap]\.m\.', full_title)):  # Contains schedule info
                            self.add_warning(f"Skipping potential false positive: {course_code} - {full_title[:50]}...")
                            i += 1
                            continue
                        
                        courses.append((i, course_code, full_title, units))
                        self.add_warning(f"Found multi-line course: {course_code} - {full_title}")
                
            i += 1
        
        return courses
    
    def parse_program(self, name: str, content: str) -> Program:
        lines = content.split('\n')
        
        # Find all course boundaries first
        course_boundaries = self.find_course_boundaries(lines)
        
        if not course_boundaries:
            # No courses found, return program with description only
            description = ' '.join(line.strip() for line in lines if line.strip())
            description = re.sub(r'\s+', ' ', description)
            return Program(
                program_name=name,
                program_description=description,
                courses=[]
            )
        
        # Extract program description (text before first course)
        first_course_line = course_boundaries[0][0]
        description_lines = []
        for i in range(first_course_line):
            if lines[i].strip():
                description_lines.append(lines[i].strip())
        
        description = ' '.join(description_lines)
        description = re.sub(r'\s+', ' ', description)
        # Apply hyphenation fixes to program description
        description = self.fix_hyphenation(description)
        
        # Parse each course
        courses = []
        for i, (start_line, course_code, course_title, units) in enumerate(course_boundaries):
            # Determine end line for this course
            if i + 1 < len(course_boundaries):
                end_line = course_boundaries[i + 1][0]
            else:
                end_line = len(lines)
            
            # Extract course lines
            course_lines = lines[start_line:end_line]
            
            # Parse this course
            course = self.parse_single_course(course_code, course_title, units, course_lines)
            courses.append(course)
        
        return Program(
            program_name=name,
            program_description=description,
            courses=courses
        )
    
    def parse_single_course(self, course_code: str, course_title: str, units: str, lines: List[str]) -> Course:
        """Parse a single course from its lines"""
        # Apply hyphenation fixes to course title
        course_title_fixed = self.fix_hyphenation(course_title)
        
        course = Course(
            course_code=course_code,
            course_title=course_title_fixed,
            units=units,
            transfer_info=[],
            special_notes=[],
            sections=[],
            description=""
        )
        
        current_section = None
        in_section = False
        description_lines = []
        
        # Skip the first line (course header)
        i = 1
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Parse transfer info
            if line.startswith('Transfer:'):
                transfer_text = line.replace('Transfer:', '').strip()
                course.transfer_info = [t.strip() for t in transfer_text.split(',')]
                i += 1
                continue
            
            # Parse C-ID
            if line.startswith('C-ID:'):
                course.c_id = line.replace('C-ID:', '').strip().rstrip('.')
                i += 1
                continue
            
            # Parse Cal-GETC area
            if line.startswith('Cal-GETC Area'):
                course.cal_getc_area = line
                i += 1
                continue
            
            # Parse bullet points
            if line.startswith('•'):
                bullet_content = line[1:].strip()
                if bullet_content.startswith('Prerequisite:'):
                    course.prerequisites = bullet_content.replace('Prerequisite:', '').strip()
                elif bullet_content.startswith('Advisory:'):
                    course.advisory = bullet_content.replace('Advisory:', '').strip()
                elif bullet_content.startswith('Satisfies'):
                    if course.special_notes is None:
                        course.special_notes = []
                    course.special_notes.append(bullet_content)
                else:
                    if course.special_notes is None:
                        course.special_notes = []
                    course.special_notes.append(bullet_content)
                i += 1
                continue
            
            # Parse "Formerly" line
            if line.startswith('Formerly'):
                course.formerly = line.replace('Formerly', '').strip().rstrip('.')
                i += 1
                continue
            
            # Check for "Please see" lines
            if line.startswith('Please see'):
                # This is typically a special instruction, not part of description
                i += 1
                continue
            
            # IMPROVED: Check for section number with validation
            section_match = re.match(r'^(\d{4})\s+(.+)', line)
            if section_match:
                potential_section_num = section_match.group(1)
                rest_of_line = section_match.group(2)
                
                # Validate that this is actually a section line
                if self.is_valid_section_line(potential_section_num, rest_of_line):
                    # Save previous section if exists
                    if current_section:
                        course.sections.append(current_section)
                    
                    # If we have accumulated description lines, save them
                    if description_lines and not course.description:
                        course.description = ' '.join(description_lines)
                        description_lines = []
                    
                    current_section = Section(
                        section_number=potential_section_num,
                        schedule=[],
                        notes=[]
                    )
                    in_section = True
                    
                    # Parse schedule from the section line itself
                    schedule = self.parse_schedule_line(rest_of_line)
                    if schedule:
                        current_section.schedule.append(schedule)
                    
                    i += 1
                    continue
                else:
                    # Not a valid section, treat as description or other content
                    if not in_section:
                        description_lines.append(line)
                    elif current_section:
                        # If we're in a section, add as a note
                        current_section.notes.append(line)
                    i += 1
                    continue
            
            # Handle lines when in section
            if in_section and current_section:
                # Try to parse as schedule (for multi-line schedules)
                schedule = self.parse_schedule_line(line)
                if schedule:
                    current_section.schedule.append(schedule)
                    i += 1
                    continue
                
                # Check if line contains section-related information or continuation of notes
                if ('section' in line.lower() or line.startswith('Above section') or 
                    line.startswith('via the Internet') or line.startswith('For additional information') or
                    line.startswith('OnlineEd.') or line.startswith('microphone for video') or
                    (line and line[0].islower())):  # Continuation lines often start with lowercase
                    current_section.notes.append(line)
                    # Extract duration if present
                    duration_match = re.search(r'meets for (\d+ weeks, .+?)(?:\.|,\s*(?:and|at))', line)
                    if duration_match:
                        current_section.duration = duration_match.group(1)
                    # Extract modality if present - search anywhere in the line
                    modality_match = re.search(r'modality is (.+?)\.?$', line)
                    if modality_match:
                        current_section.modality = modality_match.group(1).rstrip('.')
                    i += 1
                    continue
            
            # If not in section or couldn't parse as section content, it's description
            if not in_section:
                # Check for "same as" pattern
                same_as_match = re.search(r'([A-Z]+(?:\s+ST)?\s+\d+[A-Z]?)\s+is the same course as\s+([A-Z]+(?:\s+ST)?\s+\d+[A-Z]?)', line)
                if same_as_match:
                    course.same_as = same_as_match.group(2)
                    # Add the part before "same as" to description if any
                    before_same_as = line[:same_as_match.start()].strip()
                    if before_same_as:
                        description_lines.append(before_same_as)
                else:
                    description_lines.append(line)
            
            i += 1
        
        # Save last section if exists
        if current_section:
            course.sections.append(current_section)
        
        # Post-process sections to consolidate fragmented notes and extract modality
        for section in course.sections:
            # Consolidate notes that should be combined - iterate until no more changes
            notes_changed = True
            while notes_changed:
                notes_changed = False
                consolidated_notes = []
                i = 0
                
                while i < len(section.notes):
                    note = section.notes[i]
                    
                    # Check if this note is incomplete and should be combined with the next one
                    if (i + 1 < len(section.notes)):
                        next_note = section.notes[i + 1]
                        should_combine = (
                            note.endswith('and') or 
                            note.endswith('online') or 
                            note.endswith('smc.edu/') or
                            note.endswith('go to') or
                            note.endswith('Above') or
                            note.endswith('though') or  # Handle "though enrollment is open..." pattern
                            note.endswith('to smc.') or  # Handle "go to smc." patterns
                            note.endswith('Street,') or  # Handle address lines ending with "Street,"
                            'camera and' in note or 
                            'on campus and' in note or
                            next_note.startswith('OnlineEd.') or
                            next_note.startswith('edu/OnlineEd.') or  # Handle partial URL fragments
                            next_note.startswith('microphone for') or
                            next_note.startswith('For additional information') or
                            next_note.startswith('section ')
                        )
                        
                        if should_combine:
                            # Combine with next note
                            # Handle special cases for URL reconstruction
                            if (note.endswith('smc.edu/') and next_note.startswith('OnlineEd.')):
                                combined_note = note + next_note
                            elif (note.endswith('to smc.') and next_note.startswith('edu/OnlineEd.')):
                                combined_note = note + next_note
                            elif (note.endswith('Street,') and next_note.startswith('edu/OnlineEd.')):
                                # Reconstruct the full address and URL
                                combined_note = note + ' Santa Monica CA 90404. For additional information, go to smc.' + next_note
                            elif (note.endswith('/') and not next_note.startswith(' ')):
                                combined_note = note + next_note
                            else:
                                combined_note = note + ' ' + next_note
                            
                            consolidated_notes.append(combined_note)
                            i += 2  # Skip the next note since we combined it
                            notes_changed = True  # Mark that we made a change
                        else:
                            consolidated_notes.append(note)
                            i += 1
                    else:
                        consolidated_notes.append(note)
                        i += 1
                
                section.notes = consolidated_notes
            
            # Apply hyphenation fixes to all section notes
            section.notes = [self.fix_hyphenation(note) for note in section.notes]
            
            # Extract modality from any note containing "modality is"
            if not section.modality:
                for note in section.notes:
                    modality_match = re.search(r'modality is (.+?)\.?$', note)
                    if modality_match:
                        section.modality = modality_match.group(1).rstrip('.')
                        break
        
        # Post-process to establish co-enrollment relationships
        self.establish_co_enrollment_relationships(course)
        
        # IMPROVED: Validate parsed sections and remove empty/invalid ones
        course.sections = self.validate_parsed_sections(course)
        
        # Save remaining description lines
        if description_lines and not course.description:
            course.description = ' '.join(description_lines)
        
        # Clean up description and fix hyphenation
        if course.description:
            course.description = re.sub(r'\s+', ' ', course.description).strip()
            # Apply hyphenation fixes to description
            course.description = self.fix_hyphenation(course.description)
            
            # Extract and move "combined credit" statements to special_notes
            combined_credit_pattern = r'PHYSCS\s+[0-9A-Z,\s]+(?:or\s+PHYSCS\s+[0-9A-Z,\s]+)*\s+combined:\s+maximum\s+UC\s+credit,\s+1\s+series\.\s*'
            combined_match = re.search(combined_credit_pattern, course.description, re.IGNORECASE)
            if combined_match:
                combined_text = combined_match.group(0).strip()
                # Add to special_notes if not already there
                if course.special_notes is None:
                    course.special_notes = []
                if combined_text not in course.special_notes:
                    course.special_notes.append(combined_text)
                # Remove from description
                course.description = re.sub(combined_credit_pattern, '', course.description, flags=re.IGNORECASE).strip()
            
            # Clean up any leftover formatting issues in description
            # Remove redundant "WITH LAB X UNITS" that sometimes gets included
            course.description = re.sub(r'^WITH\s+LAB\s+\d+\s+UNITS\s+', '', course.description).strip()
            course.description = re.sub(r'^\d+\s+UNITS\s+', '', course.description).strip()
            # Remove redundant course name patterns at the beginning
            course.description = re.sub(r'^PHYSICS\s+\d+\s+UNITS\s+', '', course.description).strip()
            course.description = re.sub(r'^[A-Z]+\s+\d+\s+UNITS\s+', '', course.description).strip()
        
        # Apply hyphenation fixes to other text fields
        if course.prerequisites:
            course.prerequisites = self.fix_hyphenation(course.prerequisites)
        if course.advisory:
            course.advisory = self.fix_hyphenation(course.advisory)
        if course.special_notes:
            course.special_notes = [self.fix_hyphenation(note) for note in course.special_notes]
        
        return course
    
    def parse_schedule_line(self, line: str) -> Optional[Schedule]:
        """Parse a line to see if it contains schedule information"""
        # Standard time pattern - improved to handle various location/instructor formats
        # Look for time, days, then capture everything else to split manually
        # Updated to handle "Th" for Thursday - must come before single chars to avoid matching T+h separately
        time_pattern = r'(\d{1,2}:\d{2}[ap]\.m\.-\d{1,2}:\d{2}[ap]\.m\.)\s+((?:Th|[MTWRFSU])+)\s+(.+)$'
        time_match = re.match(time_pattern, line)
        
        if time_match:
            time = time_match.group(1)
            days = time_match.group(2)
            rest = time_match.group(3).strip()
            
            location, instructor = self._parse_location_instructor(rest)
            
            return Schedule(
                time=time,
                days=days,
                location=location,
                instructor=instructor
            )
        
        # Arrange pattern - improved to use robust location/instructor parsing
        arrange_pattern = r'^(Arrange-[\d.]+ Hours?)\s+(.+)$'
        arrange_match = re.match(arrange_pattern, line)
        
        if arrange_match:
            time = arrange_match.group(1)
            rest = arrange_match.group(2).strip()
            
            # Use our robust parsing method for location and instructor
            location, instructor = self._parse_location_instructor(rest)
            
            # Handle special cases for arranged schedules
            if location == "N" or location.startswith("N "):
                location = "ONLINE"
            
            return Schedule(
                time=time,
                days="N",
                location=location,
                instructor=instructor
            )
        
        return None
    
    def _parse_location_instructor(self, rest: str) -> Tuple[str, str]:
        """
        Robustly parse location and instructor from the remaining text after time and days.
        
        Strategy:
        1. Locations are typically ALL CAPS (with optional numbers/spaces)
        2. Instructor names contain lowercase letters and follow standard name patterns
        3. Use multiple approaches with validation to prevent contamination
        """
        rest = rest.strip()
        
        # Common location keywords that help identify boundaries
        location_keywords = [
            'ONLINE', 'TBA', 'ZOOM', 'REMOTE', 'CAMPUS', 'STUDIO', 'LAB', 'ROOM',
            'DRSCHR', 'BUS', 'SCI', 'TECH', 'ART', 'MUSIC', 'THEATER', 'GYM'
        ]
        
        # Method 1: Look for instructor name patterns working backwards from the end
        # Improved instructor patterns to handle various name formats:
        # - "Smith J" (last + initial)
        # - "Smith John" (last + first)  
        # - "Smith J A" (last + multiple initials)
        # - "Smith John A" (last + first + middle initial)
        # - "Williams V J" (last + spaced initials)
        instructor_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z](?:\s+[A-Z])*)*)\s*$',  # Last name + spaced initials: "Williams V J"
            r'([A-Z][a-z]+(?:\s+[A-Z][A-Z]*)*)\s*$',        # Last name + initials: "Smith JA" or "Smith J A"
            r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z])*)\s*$', # Last + First + optional initials: "Smith John A"
        ]
        
        for pattern in instructor_patterns:
            instructor_match = re.search(pattern, rest)
            if instructor_match:
                instructor = instructor_match.group(1).strip()
                location_part = rest[:instructor_match.start()].strip()
                
                # Validate that the location part looks like a location (all caps or known patterns)
                if self._is_valid_location(location_part):
                    return location_part, instructor
        
        # Method 2: Look for location patterns from the beginning
        # Match common location patterns and capture the instructor after
        location_patterns = [
            r'^((?:' + '|'.join(location_keywords) + r')(?:\s+\d+)?)\s+(.+)$',  # Known location keywords + optional room number
            r'^([A-Z]{2,}(?:\s+[A-Z0-9]+)*)\s+([A-Z][a-z].*)$',               # All caps location + instructor starting with proper case
            r'^([A-Z]+\s+\d+)\s+([A-Z][a-z].*)$',                            # Building + room number pattern
        ]
        
        for pattern in location_patterns:
            location_match = re.match(pattern, rest)
            if location_match:
                location = location_match.group(1).strip()
                instructor = location_match.group(2).strip()
                
                # Additional validation: instructor should contain lowercase
                if re.search(r'[a-z]', instructor) and not self._looks_like_location(instructor):
                    return location, instructor
        
        # Method 3: Split by detecting transition from all-caps to mixed case
        words = rest.split()
        if len(words) >= 2:
            # Find the boundary where we transition from all-caps to mixed case
            boundary_idx = None
            for i, word in enumerate(words):
                # If this word contains lowercase and isn't a known location fragment
                if re.search(r'[a-z]', word) and not self._looks_like_location(word):
                    boundary_idx = i
                    break
            
            if boundary_idx is not None and boundary_idx > 0:
                location = ' '.join(words[:boundary_idx])
                instructor = ' '.join(words[boundary_idx:])
                
                # Final validation
                if self._is_valid_location(location) and re.search(r'[a-z]', instructor):
                    return location, instructor
        
        # Method 4: Fallback - use heuristics based on common patterns
        # If we see "ONLINE" or other location keywords, handle specially
        if rest.startswith('ONLINE '):
            parts = rest.split(None, 1)
            if len(parts) >= 2:
                return 'ONLINE', parts[1]
        
        # Method 5: Handle cases where only an instructor name is present (for arrange schedules)
        # If the text looks like just a name without any location indicators
        if not any(keyword in rest.upper() for keyword in ['ONLINE', 'TBA', 'ROOM', 'BLDG', 'LAB', 'STUDIO']) and \
           len(rest.split()) >= 2 and \
           re.search(r'[a-z]', rest):  # Contains lowercase (likely an instructor name)
            # Check if it matches a typical instructor name pattern
            instructor_only_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z](?:\s+[A-Z])*)*)\s*$', rest)
            if instructor_only_match:
                # For arrange schedules, we might not have a specific location
                # Use "TBA" (To Be Announced) as the location
                return 'TBA', instructor_only_match.group(1).strip()
        
        # Last resort: if we can't parse it cleanly, put everything in location
        # This prevents contamination of instructor names
        self.add_warning(f"Could not reliably parse location/instructor from: '{rest}' - defaulting to location only")
        return rest, ""
    
    def _is_valid_location(self, text: str) -> bool:
        """Check if text looks like a valid location (building, room, etc.)"""
        if not text:
            return False
        
        # Should be mostly uppercase with optional numbers
        # Allow some flexibility for abbreviations
        words = text.split()
        for word in words:
            # Each word should be either:
            # - All uppercase letters/numbers
            # - A mix but starting with uppercase and mostly uppercase
            if not (word.isupper() or 
                    (word[0].isupper() and sum(1 for c in word if c.isupper()) >= len(word) * 0.7)):
                return False
        
        return True
    
    def _looks_like_location(self, text: str) -> bool:
        """Check if text looks like it could be part of a location"""
        location_indicators = [
            'ROOM', 'BLDG', 'BUILDING', 'FLOOR', 'ONLINE', 'CAMPUS', 'CENTER',
            'LAB', 'LABORATORY', 'STUDIO', 'HALL', 'AUDITORIUM', 'THEATER',
            'GYM', 'GYMNASIUM', 'FIELD', 'COURT'
        ]
        
        text_upper = text.upper()
        return any(indicator in text_upper for indicator in location_indicators)
    
    def save_program_json(self, program: Program):
        # Create filename from program name
        filename = re.sub(r'[^\w\s-]', '', program.program_name)
        filename = re.sub(r'[-\s]+', '_', filename).lower()
        filepath = os.path.join(self.output_dir, f"{filename}.json")
        
        # Convert to dict for JSON serialization
        program_dict = {
            "program_name": program.program_name,
            "program_description": program.program_description,
            "courses": []
        }
        
        for course in program.courses:
            course_dict = {
                "course_code": course.course_code,
                "course_title": course.course_title,
                "units": course.units,
                "transfer_info": course.transfer_info,
                "c_id": course.c_id,
                "cal_getc_area": course.cal_getc_area,
                "special_notes": course.special_notes,
                "prerequisites": course.prerequisites,
                "advisory": course.advisory,
                "formerly": course.formerly,
                "description": course.description,
                "same_as": course.same_as,
                "sections": []
            }
            
            for section in course.sections:
                section_dict = {
                    "section_number": section.section_number,
                    "schedule": [
                        {
                            "time": sched.time,
                            "days": sched.days,
                            "location": sched.location,
                            "instructor": sched.instructor
                        } for sched in section.schedule
                    ],
                    "notes": section.notes,
                    "duration": section.duration,
                    "modality": section.modality,
                    "co_enrollment_with": section.co_enrollment_with
                }
                course_dict["sections"].append(section_dict)
            
            program_dict["courses"].append(course_dict)
        
        # Save to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(program_dict, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {program.program_name} to {filepath}")
    
    def establish_co_enrollment_relationships(self, course: Course):
        """Establish co-enrollment relationships between sections based on notes"""
        for section in course.sections:
            # Join all notes for this section to handle multi-line patterns
            all_notes = ' '.join(section.notes)
            
            # Look for co-enrollment requirements in the combined notes
            co_enroll_match = re.search(r'requires co-enrollment in .+? section (\d{4})', all_notes)
            if co_enroll_match:
                section.co_enrollment_with = co_enroll_match.group(1)


# Example usage
if __name__ == "__main__":
    parser = SMCCatalogParser(os.path.join(os.path.dirname(__file__), "catalog_cleaned.txt"), os.path.join(os.path.dirname(__file__), "parsed_programs"))
    parser.parse()
    print(f"\nParsed {len(parser.programs)} programs")
    
    # Print parsing warnings summary
    if parser.parsing_warnings:
        print(f"\n=== PARSING WARNINGS ({len(parser.parsing_warnings)}) ===")
        for warning in parser.parsing_warnings[-10:]:  # Show last 10 warnings
            print(f"  {warning}")
        if len(parser.parsing_warnings) > 10:
            print(f"  ... and {len(parser.parsing_warnings) - 10} more warnings")
    
    # Print summary
    for program in parser.programs:
        print(f"\n{program.program_name}: {len(program.courses)} courses")
        for course in program.courses:
            print(f"  - {course.course_code}: {course.course_title} ({course.units})")
            if course.sections:
                print(f"    Sections: {len(course.sections)}")