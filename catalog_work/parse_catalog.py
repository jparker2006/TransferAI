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
    prerequisite_notes: Optional[str] = None
    advisory: Optional[str] = None
    advisory_notes: Optional[str] = None
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
            r'work-\s*shop': 'workshop',
            r'commen-\s*surate': 'commensurate',
            
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
    
    def is_legitimate_course_title(self, title: str) -> bool:
        """
        Determine if a title looks like a legitimate course title vs. description text.
        This is more nuanced than just checking starting words.
        """
        title_lower = title.lower()
        
        # Red flags that indicate this is likely description text, not a course title
        description_indicators = [
            # Starts with description phrases
            'this course',
            'students will',
            'the purpose of this course',
            'this class',
            'the student will',
            'in this course',
            'this program',
            
            # Contains mid-sentence indicators
            'combined: maximum uc credit',
            'maximum credit allowed',
            'see the special programs section',
            
            # Contains schedule information (shouldn't be in a title)
            r'\d{4}\s+\d{1,2}:\d{2}[ap]\.m\.',
        ]
        
        # Check for description indicators
        for indicator in description_indicators:
            if indicator.startswith('r'):  # regex pattern
                if re.search(indicator, title_lower):
                    return False
            else:
                if title_lower.startswith(indicator):
                    return False
        
        # Additional checks for overly long titles (likely descriptions)
        words = title.split()
        if len(words) > 15:  # Very long titles are suspicious
            return False
        
        # Check for legitimate course title patterns that start with articles
        # Course titles starting with articles often follow certain patterns:
        legitimate_article_patterns = [
            # "THE X OF Y" patterns common in academic course titles
            r'^the\s+\w+\s+of\s+\w+',
            r'^the\s+\w+\s+\w+',  # "THE MODERN WORLD", "THE HUMAN CONDITION"
            r'^a\s+\w+\s+to\s+\w+',  # "A GUIDE TO X", "AN INTRODUCTION TO Y"
            r'^an\s+\w+\s+to\s+\w+',
            # Common course title starters
            r'^the\s+(history|culture|art|science|study|world|modern|ancient|contemporary)',
            r'^a\s+(survey|study|guide|history|introduction)',
            r'^an\s+(introduction|overview|analysis)',
        ]
        
        # If it starts with an article, check if it matches legitimate patterns
        if title_lower.startswith(('the ', 'a ', 'an ')):
            for pattern in legitimate_article_patterns:
                if re.match(pattern, title_lower):
                    return True
            
            # If it doesn't match legitimate patterns but is short enough, be more lenient
            # Short titles starting with articles are more likely to be legitimate
            if len(words) <= 8:  # Conservative threshold for article-starting titles
                return True
            
            # If none of the patterns match and it's longer, it's probably description text
            return False
        
        # If it doesn't start with an article, apply more lenient validation
        return True
    
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
                    
                    # Use improved validation logic
                    if not self.is_legitimate_course_title(title_only):
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
                        
                        # Use improved validation logic
                        if not self.is_legitimate_course_title(full_title):
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
        
        # Fix URL spacing issues in program descriptions - handle cases like "smc.edu/ designtech" -> "smc.edu/designtech"
        # Handle all "smc.edu/ path" patterns (space after slash)
        description = re.sub(r'smc\.edu/\s+([a-zA-Z])', r'smc.edu/\1', description)
        # Handle "go to smc.edu/ path" patterns
        description = re.sub(r'go to smc\.edu/\s+([a-zA-Z])', r'go to smc.edu/\1', description)
        # Handle "or smc.edu/ path" patterns
        description = re.sub(r'or smc\.edu/\s+([a-zA-Z])', r'or smc.edu/\1', description)
        # Handle "visit smc.edu/ path" patterns
        description = re.sub(r'visit smc\.edu/\s+([a-zA-Z])', r'visit smc.edu/\1', description)
        # Handle "see smc.edu/ path" patterns
        description = re.sub(r'see smc\.edu/\s+([a-zA-Z])', r'see smc.edu/\1', description)
        
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
        please_see_lines = []  # Collect "Please see" lines separately
        
        # Skip the first line (course header) and any title continuation lines
        i = 1
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # IMPROVED: Detect and skip title continuation lines
            # These are lines that contain parts of the already-extracted course title + units
            # Check if this line looks like a title continuation with units
            units_match = re.search(r'(\d+\s+UNITS?)(?:\s|$)', line)
            if units_match:
                # Extract the part before units
                before_units = line[:units_match.start()].strip()
                extracted_units = units_match.group(1)
                
                # Check if this matches our extracted units and if the text before units 
                # appears to be part of our course title
                if extracted_units == units and before_units:
                    # Check if the text before units is likely part of the course title
                    # by seeing if it appears as a substring in our extracted title
                    # (accounting for potential differences in spacing/punctuation)
                    title_words = set(course_title.lower().replace(',', '').replace(':', '').replace('–', '').replace('-', '').split())
                    before_units_words = set(before_units.lower().replace(',', '').replace(':', '').replace('–', '').replace('-', '').split())
                    
                    # If most words in before_units appear in the course title, this is likely a continuation line
                    if before_units_words and len(before_units_words.intersection(title_words)) >= len(before_units_words) * 0.7:
                        self.add_warning(f"Skipping title continuation line: '{line}' for {course_code}")
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
            
            # IMPROVED: Parse standalone Prerequisites/Advisory lines (not in bullet format)
            if line.startswith('Prerequisites:') or line.startswith('Prerequisite:'):
                prereq_text = line.replace('Prerequisites:', '').replace('Prerequisite:', '').strip()
                course.prerequisites = prereq_text
                i += 1
                continue
            
            if line.startswith('Advisory:'):
                advisory_text = line.replace('Advisory:', '').strip()
                course.advisory = advisory_text
                i += 1
                continue
            
            # Check for "Please see" lines - collect them but don't add to main description yet
            if line.startswith('Please see'):
                please_see_lines.append(line)
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
                
                # IMPROVED: More inclusive note collection when in section
                # First check for obvious non-note content that should end the section
                if (line.startswith('Transfer:') or 
                    line.startswith('C-ID:') or 
                    line.startswith('Cal-GETC') or
                    line.startswith('Prerequisites:') or
                    line.startswith('Prerequisite:') or
                    line.startswith('Advisory:') or
                    line.startswith('Formerly') or
                    line.startswith('•') or
                    re.match(r'^[A-Z]+ \d+,', line)):  # New course starting
                    # This line belongs to course metadata, not section notes
                    # Reset section mode and reprocess this line
                    if current_section:
                        course.sections.append(current_section)
                        current_section = None
                        in_section = False
                    # Don't increment i, let the line be reprocessed in the main loop
                    continue
                
                # If we're still in section mode, treat this as a section note
                # (unless it's clearly a course description)
                if not (len(line.split()) > 15 and 
                        line[0].isupper() and 
                        '.' in line and 
                        any(word in line.lower() for word in ['course', 'students', 'study', 'topics', 'introduction'])):
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
                else:
                    # This looks like a course description, end section mode
                    if current_section:
                        course.sections.append(current_section)
                        current_section = None
                        in_section = False
                    # Let this line be processed as description in the main loop
                    # Don't increment i, let it be reprocessed
            
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
                        
                        # IMPROVED: More comprehensive should_combine logic
                        should_combine = self._should_combine_notes(note, next_note)
                        
                        if should_combine:
                            # Combine with next note
                            combined_note = self._combine_notes(note, next_note)
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
            
            # Fix URL spacing issues - handle cases like "smc.edu/ scholars" -> "smc.edu/scholars"
            for i, note in enumerate(section.notes):
                # Fix common URL spacing issues
                fixed_note = note
                # Handle all "smc.edu/ path" patterns (space after slash)
                fixed_note = re.sub(r'smc\.edu/\s+([a-zA-Z])', r'smc.edu/\1', fixed_note)
                # Handle "go to smc.edu/ path" patterns
                fixed_note = re.sub(r'go to smc\.edu/\s+([a-zA-Z])', r'go to smc.edu/\1', fixed_note)
                # Handle "or smc.edu/ path" patterns
                fixed_note = re.sub(r'or smc\.edu/\s+([a-zA-Z])', r'or smc.edu/\1', fixed_note)
                # Handle "visit smc.edu/ path" patterns
                fixed_note = re.sub(r'visit smc\.edu/\s+([a-zA-Z])', r'visit smc.edu/\1', fixed_note)
                # Handle "see smc.edu/ path" patterns
                fixed_note = re.sub(r'see smc\.edu/\s+([a-zA-Z])', r'see smc.edu/\1', fixed_note)
                section.notes[i] = fixed_note
            
            # Extract modality from any note containing "modality is"
            if not section.modality:
                for note in section.notes:
                    # Primary pattern: "modality is [value]"
                    modality_match = re.search(r'modality is (.+?)\.?$', note)
                    if modality_match:
                        section.modality = modality_match.group(1).rstrip('.')
                        break
                    
                    # IMPROVED: Additional modality patterns
                    # "is a hybrid class"
                    if re.search(r'is a hybrid class', note, re.IGNORECASE):
                        section.modality = 'Hybrid'
                        break
                    
                    # "is an online class"  
                    if re.search(r'is an? online class', note, re.IGNORECASE):
                        section.modality = 'Online'
                        break
                    
                    # "hybrid class taught on campus and online"
                    if re.search(r'hybrid class taught', note, re.IGNORECASE):
                        section.modality = 'Hybrid'
                        break
                    
                    # "taught on campus and online" (without "hybrid" but with both)
                    if re.search(r'taught on campus and online', note, re.IGNORECASE):
                        section.modality = 'Hybrid'
                        break
        
        # Post-process to establish co-enrollment relationships
        self.establish_co_enrollment_relationships(course)
        
        # IMPROVED: Validate parsed sections and remove empty/invalid ones
        course.sections = self.validate_parsed_sections(course)
        
        # Save remaining description lines
        if description_lines and not course.description:
            course.description = ' '.join(description_lines)
        
        # If no description but we have "Please see" lines, use those as description
        if not course.description and please_see_lines:
            course.description = ' '.join(please_see_lines)
            self.add_warning(f"Using 'Please see' line as description for {course_code}: {course.description}")
        
        # Clean up description and fix hyphenation
        if course.description:
            course.description = re.sub(r'\s+', ' ', course.description).strip()
            # Apply hyphenation fixes to description
            course.description = self.fix_hyphenation(course.description)
            
            # IMPROVED: Extract prerequisites from description if they got misplaced there
            # Handle patterns like "Prerequisites: COURSE 1 and COURSE 2." at the beginning of description
            prereq_pattern = r'^(Prerequisites?:\s*[^.]+\.)\s*'
            prereq_match = re.match(prereq_pattern, course.description)
            if prereq_match and not course.prerequisites:
                prereq_text = prereq_match.group(1)
                # Extract just the prerequisite content without the label
                course.prerequisites = prereq_text.replace('Prerequisites:', '').replace('Prerequisite:', '').strip().rstrip('.')
                # Remove from description
                course.description = re.sub(prereq_pattern, '', course.description).strip()
                self.add_warning(f"Extracted prerequisites from description for {course_code}: {course.prerequisites}")
            
            # IMPROVED: Extract all asterisk notes from description and categorize them
            asterisk_patterns = [
                # Credit limitations and restrictions (should go to special_notes)
                # Updated to handle sentences ending with or without periods
                (r'(\*Maximum (?:UC )?credit[^.]*(?:\.|(?=\s+[A-Z])))', 'special'),
                (r'(\*No UC (?:transfer )?credit[^.]*(?:\.|(?=\s+[A-Z])))', 'special'),
                (r'(\*Total of[^.]*(?:\.|(?=\s+[A-Z])))', 'special'),
                (r'(\*UC gives no credit[^.]*(?:\.|(?=\s+[A-Z])))', 'special'),
                # Handle ESL-style combined credit patterns
                (r'(\*[A-Z]+ \d+[A-Z]?,\s*[A-Z]+ \d+[A-Z]?[^:]*:\s*maximum credit[^.]*(?:\.|(?=\s+[A-Z])))', 'special'),
                
                # Prerequisite explanations (should go to prerequisite_notes)
                (r'(\*The prerequisite for this course[^.]*(?:\.|(?=\s+[A-Z])))', 'prerequisite'),
                
                # Advisory explanations (should go to advisory_notes)
                (r'(\*The advisory for this course[^.]*(?:\.|(?=\s+[A-Z])))', 'advisory'),
            ]
            
            for pattern, note_type in asterisk_patterns:
                match = re.search(pattern, course.description)
                if match:
                    asterisk_note = match.group(1)
                    
                    if note_type == 'special':
                        # Add to special_notes
                        if course.special_notes is None:
                            course.special_notes = []
                        course.special_notes.append(asterisk_note)
                        self.add_warning(f"Extracted credit note from description for {course_code}: {asterisk_note}")
                    elif note_type == 'prerequisite':
                        # Put explanation in prerequisite_notes field
                        course.prerequisite_notes = asterisk_note
                        self.add_warning(f"Extracted prerequisite explanation from description for {course_code}: {asterisk_note}")
                    elif note_type == 'advisory':
                        # Put explanation in advisory_notes field
                        course.advisory_notes = asterisk_note
                        self.add_warning(f"Extracted advisory explanation from description for {course_code}: {asterisk_note}")
                    
                    # Remove from description
                    course.description = re.sub(pattern, '', course.description).strip()
            
            # Clean up advisory field by removing asterisks and trailing periods
            if course.advisory:
                course.advisory = course.advisory.rstrip('*. ')
            
            # Fix URL spacing issues in descriptions - handle cases like "smc.edu/ scholars" -> "smc.edu/scholars"
            # Handle all "smc.edu/ path" patterns (space after slash)
            course.description = re.sub(r'smc\.edu/\s+([a-zA-Z])', r'smc.edu/\1', course.description)
            # Handle "go to smc.edu/ path" patterns
            course.description = re.sub(r'go to smc\.edu/\s+([a-zA-Z])', r'go to smc.edu/\1', course.description)
            # Handle "or smc.edu/ path" patterns
            course.description = re.sub(r'or smc\.edu/\s+([a-zA-Z])', r'or smc.edu/\1', course.description)
            # Handle "visit smc.edu/ path" patterns
            course.description = re.sub(r'visit smc\.edu/\s+([a-zA-Z])', r'visit smc.edu/\1', course.description)
            # Handle "see smc.edu/ path" patterns
            course.description = re.sub(r'see smc\.edu/\s+([a-zA-Z])', r'see smc.edu/\1', course.description)
            
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
        if course.prerequisite_notes:
            course.prerequisite_notes = self.fix_hyphenation(course.prerequisite_notes)
        if course.advisory:
            course.advisory = self.fix_hyphenation(course.advisory)
        if course.advisory_notes:
            course.advisory_notes = self.fix_hyphenation(course.advisory_notes)
        if course.special_notes:
            course.special_notes = [self.fix_hyphenation(note) for note in course.special_notes]
            # Also fix URL spacing issues in special_notes
            for i, note in enumerate(course.special_notes):
                fixed_note = note
                # Handle all "smc.edu/ path" patterns (space after slash)
                fixed_note = re.sub(r'smc\.edu/\s+([a-zA-Z])', r'smc.edu/\1', fixed_note)
                # Handle "go to smc.edu/ path" patterns
                fixed_note = re.sub(r'go to smc\.edu/\s+([a-zA-Z])', r'go to smc.edu/\1', fixed_note)
                # Handle "or smc.edu/ path" patterns
                fixed_note = re.sub(r'or smc\.edu/\s+([a-zA-Z])', r'or smc.edu/\1', fixed_note)
                # Handle "visit smc.edu/ path" patterns
                fixed_note = re.sub(r'visit smc\.edu/\s+([a-zA-Z])', r'visit smc.edu/\1', fixed_note)
                # Handle "see smc.edu/ path" patterns
                fixed_note = re.sub(r'see smc\.edu/\s+([a-zA-Z])', r'see smc.edu/\1', fixed_note)
                course.special_notes[i] = fixed_note
        
        return course
    
    def _should_combine_notes(self, note: str, next_note: str) -> bool:
        """
        Determine if two consecutive notes should be combined.
        Uses multiple heuristics to detect incomplete sentences/fragments.
        """
        # Original explicit patterns (keep these for known cases)
        explicit_patterns = (
            note.endswith('and') or 
            note.endswith('online') or 
            note.endswith('smc.edu/') or
            note.endswith('go to') or
            note.endswith('Above') or
            note.endswith('though') or  # Handle "though enrollment is open..." pattern
            note.endswith('to smc.') or  # Handle "go to smc." patterns
            note.endswith('Street,') or  # Handle address lines ending with "Street,"
            note.endswith('at') or  # Handle "located at" patterns
            note.endswith('the') or  # Handle "the [next line]" patterns
            note.endswith('of') or   # Handle "of [next line]" patterns
            note.endswith('in') or   # Handle "in [next line]" patterns
            note.endswith('for') or  # Handle "for [next line]" patterns
            note.endswith('on') or   # Handle "on [next line]" patterns
            note.endswith('via') or  # Handle "via [next line]" patterns
            note.endswith('with') or # Handle "with [next line]" patterns
            'camera and' in note or 
            'on campus and' in note or
            next_note.startswith('OnlineEd.') or
            next_note.startswith('edu/OnlineEd.') or  # Handle partial URL fragments
            next_note.startswith('microphone for') or
            next_note.startswith('For additional information') or
            next_note.startswith('section ')
        )
        
        if explicit_patterns:
            return True
        
        # NEW: Detect sentence fragments based on capitalization and punctuation
        note_ends_with_incomplete = (
            # Ends with a word that doesn't look like a complete thought
            not note.endswith('.') and 
            not note.endswith('!') and
            not note.endswith('?') and
            not note.endswith(':') and
            # And the next note starts with lowercase (likely continuation)
            next_note and next_note[0].islower()
        )
        
        if note_ends_with_incomplete:
            return True
        
        # NEW: Detect proper noun continuations (like "Santa" + "Monica")
        # Look for cases where the last word of note might be part of a proper noun
        # that continues in the next note
        note_words = note.split()
        if note_words:
            last_word = note_words[-1].rstrip('.,;:')
            next_words = next_note.split()
            if next_words:
                first_word = next_words[0].rstrip('.,;:')
                
                # Check if this looks like a proper noun continuation
                # Both parts should be capitalized and neither should be common sentence starters
                if (last_word and last_word[0].isupper() and 
                    first_word and first_word[0].isupper() and
                    first_word not in ['Above', 'This', 'The', 'For', 'Students', 'Section']):
                    return True
        
        # NEW: Detect address/location patterns
        # Common patterns: "Street, Santa Monica", "Boulevard, Los Angeles", etc.
        if (note.endswith(',') and 
            any(addr in note.lower() for addr in ['street', 'avenue', 'boulevard', 'drive', 'road', 'lane'])):
            return True
        
        return False
    
    def _combine_notes(self, note: str, next_note: str) -> str:
        """
        Intelligently combine two notes, handling special cases for URLs, addresses, etc.
        """
        # Handle special cases for URL reconstruction
        if (note.endswith('smc.edu/') and next_note.startswith('OnlineEd.')):
            return note + next_note
        elif (note.endswith('to smc.') and next_note.startswith('edu/OnlineEd.')):
            return note + next_note
        elif (note.endswith('Street,') and next_note.startswith('edu/OnlineEd.')):
            # Reconstruct the full address and URL
            return note + ' Santa Monica CA 90404. For additional information, go to smc.' + next_note
        elif (note.endswith('/') and not next_note.startswith(' ')):
            return note + next_note
        else:
            # Default: add space between notes
            return note + ' ' + next_note
    
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
                "prerequisite_notes": course.prerequisite_notes,
                "advisory": course.advisory,
                "advisory_notes": course.advisory_notes,
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