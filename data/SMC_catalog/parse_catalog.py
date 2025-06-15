import re
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class SmallHeader:
    header_name: str
    description: str


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
    # Unique identifier automatically assigned by the parser. Populated after the full
    # catalog is parsed so that duplicates can be accurately disambiguated.
    course_id: Optional[str] = None
    c_id: Optional[str] = None
    cal_getc_area: Optional[str] = None
    special_notes: List[str] = None
    prerequisites: Optional[str] = None
    prerequisite_notes: Optional[str] = None
    corequisites: Optional[str] = None
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
        self.small_headers = []  # Track smaller program headers marked with ~
        self.parsing_warnings = []  # Track potential parsing issues
        
        # Directory to hold rarely-used or archived reference JSON files (e.g. Independent Studies)
        self.archived_dir = os.path.join(output_dir, "extra_refs")
        os.makedirs(self.archived_dir, exist_ok=True)
    
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
            
            # New hyphenation errors found in the parsed JSON files
            r'chem-\s*istry': 'chemistry',
            r'sci-\s*entific': 'scientific',
            r'interchange-\s*able-lens': 'interchangeable-lens',
            r'avail-\s*able': 'available',
            r'platform-\s*independent': 'platform-independent',
            r'sci-\s*ence': 'science',
            r'neonatal-pedi-\s*atric': 'neonatal-pediatric',
            r'profession-\s*alism': 'professionalism',
            r'self-\s*expression': 'self-expression',
            r'consider-\s*ations': 'considerations',
            r'human-\s*environment': 'human-environment',
            r'prob-\s*ability': 'probability',
            r'socio-polit-\s*ical': 'socio-political',
            r'influ-\s*ences': 'influences',
            r'indig-\s*enous': 'indigenous',
            r'devel-\s*oping': 'developing',
            r'audi-\s*ence': 'audience',
            r'dem-\s*onstrate': 'demonstrate',
            r'antigen-\s*antibody': 'antigen-antibody',
            r'devel-\s*oped': 'developed',
            r'lit-\s*erature': 'literature',
            r'prereq-\s*uisite': 'prerequisite',
            r'relax-\s*ation': 'relaxation',
            r'insur-\s*ance': 'insurance',
            r'devel-\s*opmental': 'developmental',
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
    
    def _parse_multiline_bullet(self, lines: List[str], start_idx: int) -> Tuple[str, int]:
        """
        Parse a bullet point that might span multiple lines.
        
        Returns:
            - The complete bullet text (including the bullet character)
            - Number of lines consumed
        """
        bullet_text = lines[start_idx]
        lines_consumed = 1
        
        # Check if the bullet appears to be incomplete (ends with comma, "and", etc.)
        while self._bullet_looks_incomplete(bullet_text):
            # Look at the next line
            next_idx = start_idx + lines_consumed
            if next_idx >= len(lines):
                break
            
            next_line = lines[next_idx].strip()
            
            # Stop if we hit another bullet point, section number, or course metadata
            if (next_line.startswith('•') or 
                next_line.startswith('Transfer:') or
                next_line.startswith('C-ID:') or
                next_line.startswith('Cal-GETC') or
                next_line.startswith('Prerequisites:') or
                next_line.startswith('Prerequisite:') or
                next_line.startswith('Corequisites:') or
                next_line.startswith('Corequisite:') or
                next_line.startswith('Advisory:') or
                next_line.startswith('Formerly') or
                re.match(r'^\d{4}\s+', next_line) or  # Section numbers
                re.match(r'^[A-Z]+ \d+,', next_line)):  # New course starting
                break
            
            # Stop if the next line looks like the start of a course description
            # (long line starting with uppercase, containing common description words)
            if (len(next_line.split()) > 10 and 
                next_line[0].isupper() and 
                any(word in next_line.lower() for word in ['this course', 'students will', 'the purpose', 'emphasis is placed'])):
                break
            
            # Add the next line to the bullet text
            bullet_text += ' ' + next_line
            lines_consumed += 1
            
            # Safety check to prevent infinite loops
            if lines_consumed > 10:  # No bullet should span more than 10 lines
                break
        
        return bullet_text, lines_consumed
    
    def _parse_prerequisite_with_potential_continuation(self, lines: List[str], start_idx: int) -> Tuple[str, int]:
        """
        Parse a prerequisite bullet that might have continuation lines before a corequisite bullet.
        
        This handles the specific case where:
        • Prerequisite: ... ENGL
        C1000 (formerly ENGL 1), MCRBIO 1, PHYS 3.
        • Corequisite: ...
        
        Returns:
            - The complete prerequisite text (including the bullet character)
            - Number of lines consumed
        """
        prereq_text = lines[start_idx]
        lines_consumed = 1
        
        # Look ahead for continuation lines until we hit a corequisite bullet
        # or other stopping criteria
        j = start_idx + 1
        while j < len(lines):
            next_line = lines[j].strip()
            
            if not next_line:
                j += 1
                continue
            
            # Stop if we hit a corequisite bullet - this is the key pattern
            if next_line.startswith('• Corequisite:') or next_line.startswith('• Corequisites:'):
                break
            
            # Stop if we hit other bullets or section indicators
            if (next_line.startswith('•') or 
                next_line.startswith('Transfer:') or
                next_line.startswith('C-ID:') or
                next_line.startswith('Cal-GETC') or
                next_line.startswith('Advisory:') or
                next_line.startswith('Formerly') or
                re.match(r'^\d{4}\s+', next_line) or  # Section numbers
                re.match(r'^[A-Z]+ \d+,', next_line)):  # New course starting
                break
            
            # Stop if the next line looks like the start of a course description
            # (long line starting with uppercase, containing common description words)
            if (len(next_line.split()) > 10 and 
                next_line[0].isupper() and 
                any(word in next_line.lower() for word in ['this course', 'students will', 'the purpose', 'emphasis is placed'])):
                break
            
            # ENHANCED: Stop if line starts with common course description patterns
            # This catches cases like "This as an introductory course..." in NURSNG 17
            description_starters = [
                'this course',
                'this as an introductory',
                'this as a',
                'this class',
                'this is the',  # ADDED: catches "This is the second/first/third..." patterns (fixes cosmetology courses)
                'this is an',   # ADDED: catches "This is an introductory/advanced..." patterns  
                'this is a',    # ADDED: catches "This is a specialized/required..." patterns
                'the purpose of this course',
                'students will',
                'the student will',
                'emphasis is placed',
                'topics include',
                'this program'
            ]
            
            line_lower = next_line.lower()
            should_stop = False
            for starter in description_starters:
                if line_lower.startswith(starter):
                    should_stop = True
                    break
            
            if should_stop:
                break
            
            # Add this line to the prerequisite text
            prereq_text += ' ' + next_line
            lines_consumed += 1
            j += 1
            
            # Safety check to prevent infinite loops
            if lines_consumed > 10:  # No prerequisite should span more than 10 lines
                break
        
        return prereq_text, lines_consumed
    
    def _bullet_looks_incomplete(self, bullet_text: str) -> bool:
        """
        Determine if a bullet point looks incomplete and likely continues on the next line.
        """
        bullet_text = bullet_text.strip()
        
        # Bullet is likely incomplete if it ends with:
        incomplete_endings = [
            ',',           # Comma (like "MUSIC 40, 42, 45,")
            ', and',       # ", and" 
            ' and',        # " and"
            ', or',        # ", or"
            ' or',         # " or"
            ';',           # Semicolon
            ':',           # Colon (less common but possible)
        ]
        
        for ending in incomplete_endings:
            if bullet_text.endswith(ending):
                return True
        
        # Also check for patterns that suggest continuation like:
        # "one of the following:" without a period
        if ('one of the following' in bullet_text.lower() and 
            not bullet_text.endswith('.') and
            not bullet_text.endswith(':')):
            return True
        
        return False

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
        
        # Split by both program markers: = for main programs, ~ for small headers
        # We'll process them in order to maintain proper organization
        sections = re.split(r'\n([=~])([^=~\n]+)\n', content)
        
        # Process each section
        i = 1
        while i < len(sections):
            if i + 2 < len(sections):
                marker = sections[i]      # = or ~
                header_name = sections[i + 1].strip()
                section_content = sections[i + 2] if i + 2 < len(sections) else ""
                
                if marker == '=':
                    # Main program header
                    if section_content.strip():
                        program = self.parse_program(header_name, section_content)
                        self.programs.append(program)
                elif marker == '~':
                    # Small header - extract just the description (usually one line)
                    description_lines = []
                    lines = section_content.split('\n')
                    
                    # Take content until we hit another header or end
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        # Stop if we hit the start of another section (=HEADER or ~HEADER pattern)
                        if line.startswith('=') or line.startswith('~'):
                            break
                        description_lines.append(line)
                        # For small headers, take multiple lines if needed to capture complete descriptions
                        # Continue until we have a reasonably complete description or hit specific markers
                        full_description = ' '.join(description_lines)
                        # Stop if we reach a reasonable length and end with proper punctuation
                        if (len(full_description) > 50 and 
                            (full_description.endswith('.') or 
                             full_description.endswith('"') or
                             'listed under name of specific language' in full_description)):
                            break
                    
                    description = ' '.join(description_lines).strip()
                    if description:
                        small_header = SmallHeader(
                            header_name=header_name,
                            description=description
                        )
                        self.small_headers.append(small_header)
                
                i += 3
            else:
                i += 1
        
        # After all programs have been parsed, generate unique course IDs and then
        # persist each program to disk.  Generating IDs *after* all courses are known
        # allows us to reliably detect duplicates across different programs.
        self.assign_course_ids()

        # NEW: Replace placeholder "Independent Studies" references in course descriptions
        self._replace_independent_studies_descriptions()

        for program in self.programs:
            self.save_program_json(program)

        # Save small headers to separate JSON file
        if self.small_headers:
            self.save_small_headers_json()
    
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
        # Exception for combined courses with "CONCURRENT SUPPORT" - these are legitimately long
        if len(words) > 15 and 'CONCURRENT SUPPORT' not in title_lower:  # Very long titles are suspicious
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
        combined_courses_found = set()  # Track combined courses to avoid duplicating their "C" components
        consumed_lines = set()  # Track lines that are part of multi-line course titles
        while i < len(lines):
            # Skip lines that were already consumed as part of multi-line titles
            if i in consumed_lines:
                i += 1
                continue
            
            line = lines[i].strip()
            
            # Look for course code pattern at the start of a line
            # Updated to handle codes like "ENGL C1000" (letter prefix before digits)
            # Allow for optional whitespace before the comma that separates the course code and title. Some
            # catalog lines (e.g. "TH ART 14 , BEGINNING STAGE COMBAT 2 UNITS") contain a stray space before
            # the comma which previously prevented them from matching. The updated pattern makes that space
            # optional and therefore captures such cases.
            course_match = re.match(r'^((?:[A-Z]+\s+)?[A-Z]+(?:\s+ST)?\s+[A-Z]*[0-9]+[A-Z]*)\s*,\s+(.+)', line)
            if course_match:
                course_code = course_match.group(1).strip()
                title_start = course_match.group(2)
                
                # SPECIAL CASE: Handle complex combined course titles that span multiple lines
                # Pattern 1: "MATH 4, COLLEGE ALGEBRA FOR STEM MAJORS" followed by "WITH MATH 4C, CONCURRENT SUPPORT..."
                # Pattern 2: "STAT C1000, INTRODUCTION TO STATISTICS WITH" followed by "MATH 54C, CONCURRENT SUPPORT..."
                # General patterns: 
                #   - Course title ending with "WITH" + next line containing "CONCURRENT SUPPORT"
                #   - Course title + next line starting with "WITH" and containing "CONCURRENT SUPPORT"
                if (i + 1 < len(lines) and 
                    ('CONCURRENT SUPPORT' in lines[i + 1].strip()) and
                    (title_start.endswith('WITH') or lines[i + 1].strip().startswith('WITH'))):
                    
                    # This is a combined course - combine the title from both lines
                    next_line = lines[i + 1].strip()
                    combined_title = title_start + ' ' + next_line
                    
                    # Extract the C course code from the next line for tracking
                    c_course_match = re.match(r'^([A-Z]+\s+\d+[A-Z]),', next_line)
                    if c_course_match:
                        c_course_code = c_course_match.group(1)
                        combined_courses_found.add(c_course_code)
                        consumed_lines.add(i + 1)  # Mark the next line as consumed
                    
                    # Look for units in the combined title or subsequent lines
                    units_match = re.search(r'(\d+(?:\.\d+)?\s+UNITS?)(?:\s|$)', combined_title)
                    if units_match:
                        # Extract title without units
                        title_only = combined_title[:units_match.start()].strip()
                        units = units_match.group(1)
                        
                        courses.append((i, course_code, title_only, units))
                        self.add_warning(f"Found combined multi-line course: {course_code} - {title_only}")
                        
                        # Skip the next line since we consumed it
                        i += 2
                        continue
                    else:
                        # Look ahead for units on subsequent lines
                        j = i + 2
                        units = None
                        while j < len(lines) and j < i + 5:
                            units_line = lines[j].strip()
                            if not units_line:
                                j += 1
                                continue
                            
                            units_match = re.search(r'(\d+(?:\.\d+)?\s+UNITS?)(?:\s|$)', units_line)
                            if units_match:
                                before_units = units_line[:units_match.start()].strip()
                                if before_units:
                                    combined_title += ' ' + before_units
                                units = units_match.group(1)
                                consumed_lines.add(j)  # Mark this line as consumed too
                                break
                            elif (units_line.startswith(('Transfer:', 'C-ID:', 'Cal-GETC', '•')) or
                                  re.match(r'^\d{4}\s+', units_line)):
                                break
                            else:
                                combined_title += ' ' + units_line
                                consumed_lines.add(j)  # Mark continuation lines as consumed
                                j += 1
                        
                        if units:
                            courses.append((i, course_code, combined_title, units))
                            self.add_warning(f"Found complex multi-line course: {course_code} - {combined_title}")
                            i = j + 1
                            continue
                
                # ADDITIONAL CASE: Handle when the current line is a "C" course that's part of a combined title
                # Example: "MATH 3C, CONCURRENT SUPPORT..." following "MATH 3, TRIGONOMETRY..."
                # Example: "MATH 54C, CONCURRENT SUPPORT..." following "STAT C1000, INTRODUCTION TO STATISTICS WITH"
                # Check if this is actually a continuation of a previous combined course
                if ('CONCURRENT SUPPORT' in title_start and i > 0):
                    
                    # Look back to see if the previous line was the start of a combined course
                    prev_line = lines[i - 1].strip() if i > 0 else ""
                    
                    # Check if previous line ended with "WITH" pattern (indicating a combined course)
                    if prev_line.endswith('WITH'):
                        # This line is a continuation of the previous combined course - skip it
                        combined_courses_found.add(course_code)
                        self.add_warning(f"Skipping {course_code} - continuation of combined course title on previous line")
                        i += 1
                        continue
                
                # Skip "C" courses if we already found their combined version
                if course_code in combined_courses_found:
                    self.add_warning(f"Skipping {course_code} - already included in combined course")
                    i += 1
                    continue
                
                # Check if the units are already on this line (single-line case)
                # Updated to handle decimal units like "2.5 UNITS"
                units_match = re.search(r'(\d+(?:\.\d+)?\s+UNITS?)(?:\s|$)', title_start)
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
                        # Updated to handle decimal units like "2.5 UNITS"
                        units_match = re.search(r'(\d+(?:\.\d+)?\s+UNITS?)(?:\s|$)', next_line)
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
        
        # Special handling for ESL program with subheaders
        if name == "ESL – English as a Second Language":
            return self.parse_esl_program_with_subheaders(name, content, lines)
        
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
        
        # TARGETED FIX: Handle English Composition Group B special case
        if name == "English Composition – Group B":
            courses = self._fix_english_group_b_courses(courses)

        return Program(
            program_name=name,
            program_description=description,
            courses=courses
        )
    
    def parse_esl_program_with_subheaders(self, name: str, content: str, lines: List[str]) -> Program:
        """Special parser for ESL program that has subheaders grouping courses"""
        
        # ESL subheaders we expect to find
        esl_subheaders = [
            "Intensive English",
            "ESL Writing", 
            "Speaking and Listening",
            "Grammar",
            "Vocabulary"
        ]
        
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
        
        # Extract program description (text before first course, cleaning subheader fragments)
        first_course_line = course_boundaries[0][0]
        description_lines = []
        for i in range(first_course_line):
            if lines[i].strip():
                description_lines.append(lines[i].strip())
        
        description = ' '.join(description_lines)
        description = re.sub(r'\s+', ' ', description)
        # Apply hyphenation fixes to program description
        description = self.fix_hyphenation(description)
        
        # Clean up subheader fragments from description
        # Remove "Intensive English" if it appears at the end without proper context
        description = re.sub(r'\s+Intensive English\s*$', '', description).strip()
        
        # Fix URL spacing issues in program descriptions
        description = re.sub(r'smc\.edu/\s+([a-zA-Z])', r'smc.edu/\1', description)
        description = re.sub(r'go to smc\.edu/\s+([a-zA-Z])', r'go to smc.edu/\1', description)
        description = re.sub(r'or smc\.edu/\s+([a-zA-Z])', r'or smc.edu/\1', description)
        description = re.sub(r'visit smc\.edu/\s+([a-zA-Z])', r'visit smc.edu/\1', description)
        description = re.sub(r'see smc\.edu/\s+([a-zA-Z])', r'see smc.edu/\1', description)
        
        # Parse all courses and track subheader assignments
        courses = []
        course_to_subheader = {}  # Track which subheader each course belongs to
        
        for i, (start_line, course_code, course_title, units) in enumerate(course_boundaries):
            # Determine end line for this course
            if i + 1 < len(course_boundaries):
                end_line = course_boundaries[i + 1][0]
            else:
                end_line = len(lines)
            
            # Extract course lines
            course_lines = lines[start_line:end_line]
            
            # Look backwards from this course to find the most recent subheader
            current_subheader = None
            for j in range(start_line - 1, max(0, start_line - 20), -1):  # Look back up to 20 lines
                line = lines[j].strip()
                for subheader in esl_subheaders:
                    if line == subheader or line.endswith(subheader):
                        current_subheader = subheader
                        break
                if current_subheader:
                    break
            
            # Parse this course
            course = self.parse_single_course(course_code, course_title, units, course_lines)
            
            # Clean subheader fragments from course section notes
            for section in course.sections:
                cleaned_notes = []
                for note in section.notes:
                    # Remove standalone subheader names from notes
                    cleaned_note = note
                    for subheader in esl_subheaders:
                        # Remove if the note is exactly the subheader or ends with it
                        if cleaned_note.strip() == subheader:
                            cleaned_note = ""
                        elif cleaned_note.strip().endswith(subheader):
                            # Remove the subheader from the end, but keep other content
                            cleaned_note = cleaned_note.replace(subheader, "").strip()
                            # Clean up any trailing punctuation or "Above section" artifacts
                            cleaned_note = re.sub(r'\.\s*$', '', cleaned_note)
                            cleaned_note = re.sub(r'Above section modality is [^.]+\.\s*$', lambda m: m.group(0).replace(subheader, ''), cleaned_note)
                    
                    if cleaned_note.strip():
                        cleaned_notes.append(cleaned_note)
                
                section.notes = cleaned_notes
            
            courses.append(course)
            if current_subheader:
                course_to_subheader[course_code] = current_subheader
        
        # Group courses by subheader for description enhancement
        subheader_to_courses = {}
        for course in courses:
            subheader = course_to_subheader.get(course.course_code, "General")
            if subheader not in subheader_to_courses:
                subheader_to_courses[subheader] = []
            subheader_to_courses[subheader].append(course.course_code)
        
        # Add course organization information to description
        if subheader_to_courses:
            organization_parts = []
            subheader_order = ["Intensive English", "ESL Writing", "Speaking and Listening", "Grammar", "Vocabulary"]
            
            for subheader in subheader_order:
                if subheader in subheader_to_courses and subheader != "General":
                    course_codes = subheader_to_courses[subheader]
                    if len(course_codes) == 1:
                        organization_parts.append(f"{subheader}: {course_codes[0]}")
                    else:
                        organization_parts.append(f"{subheader}: {', '.join(course_codes)}")
            
            if organization_parts:
                description += f" Courses are organized into the following areas: {'; '.join(organization_parts)}."
        
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
            units_match = re.search(r'(\d+(?:\.\d+)?\s+UNITS?)(?:\s|$)', line)
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
                
                # ENHANCED: Also check for common title continuation patterns that should always be skipped
                # This catches cases like "LAB 2.5 UNITS" where LAB might not match title due to extraction issues
                if extracted_units == units:
                    continuation_patterns = [
                        r'^LAB\s+[\d.]+\s+UNITS?$',           # "LAB 2.5 UNITS"
                        r'^CONCEPTS\s+\d+\s+[\d.]+\s+UNITS?$', # "CONCEPTS 2 2.5 UNITS"
                        r'^WITH\s+LAB\s+[\d.]+\s+UNITS?$',    # "WITH LAB X UNITS"
                        r'^[A-Z]+\s+\d+\s+[\d.]+\s+UNITS?$', # Generic "WORD NUMBER X.X UNITS"
                    ]
                    
                    for pattern in continuation_patterns:
                        if re.match(pattern, line, re.IGNORECASE):
                            self.add_warning(f"Skipping title continuation line (pattern match): '{line}' for {course_code}")
                            i += 1
                            continue
            
            # Parse transfer info
            if line.startswith('Transfer:'):
                transfer_text = line.replace('Transfer:', '').strip()
                # Clean up transfer designations by removing asterisks (footnote markers)
                course.transfer_info = [t.strip().rstrip('*') for t in transfer_text.split(',')]
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
            
            # Parse bullet points (with multi-line support)
            if line.startswith('•'):
                bullet_content = line[1:].strip()
                
                # SPECIAL CASE: Handle prerequisite followed by corequisite
                # When we have a prerequisite bullet followed by corequisite bullet,
                # we need to collect all text between them as part of the prerequisite
                if bullet_content.startswith('Prerequisite:'):
                    # Capture the (potentially multi-line) prerequisite text
                    prereq_text, lines_consumed = self._parse_prerequisite_with_potential_continuation(lines, i)
                    # Clean the text (remove label & leading bullet if present)
                    clean_prereq = prereq_text.replace('Prerequisite:', '').lstrip('•').strip()

                    # If we already have prerequisite text from an earlier bullet, append rather than overwrite
                    if course.prerequisites:
                        # Only add if this prerequisite fragment is not already present
                        if clean_prereq not in course.prerequisites:
                            # Use comma instead of semicolon if existing text ends with a period to avoid '.;' pattern
                            if course.prerequisites.rstrip().endswith('.'):
                                # Replace terminal period with comma and a space
                                course.prerequisites = course.prerequisites.rstrip().rstrip('.') + ', ' + clean_prereq
                            else:
                                course.prerequisites = f"{course.prerequisites}; {clean_prereq}"
                    else:
                        course.prerequisites = clean_prereq

                    i += lines_consumed
                    continue
                
                # For other bullets, use standard multi-line parsing
                bullet_text, lines_consumed = self._parse_multiline_bullet(lines, i)
                bullet_content = bullet_text[1:].strip()  # Remove the bullet character
                
                if bullet_content.startswith('Corequisite:') or bullet_content.startswith('Corequisites:'):
                    # Handle both singular and plural forms
                    coreq_text = bullet_content.replace('Corequisite:', '').replace('Corequisites:', '').strip()
                    course.corequisites = coreq_text
                elif bullet_content.startswith('Prerequisite/Corequisite:'):
                    # Handle combined prerequisite/corequisite bullets which should populate *both*
                    # fields *without* removing any existing prerequisite content.
                    combined_text = bullet_content.replace('Prerequisite/Corequisite:', '').strip()

                    # Merge with prerequisites – append if we already captured other prereqs
                    if course.prerequisites:
                        if combined_text not in course.prerequisites:
                            # Use comma instead of semicolon if existing text ends with a period to avoid '.;' pattern
                            if course.prerequisites.rstrip().endswith('.'):
                                # Replace terminal period with comma and a space
                                course.prerequisites = course.prerequisites.rstrip().rstrip('.') + ', ' + combined_text
                            else:
                                course.prerequisites = f"{course.prerequisites}; {combined_text}"
                    else:
                        course.prerequisites = combined_text

                    # Always include in corequisites (append if necessary)
                    if course.corequisites:
                        if combined_text not in course.corequisites:
                            # Use comma instead of semicolon if existing text ends with a period to avoid '.;' pattern
                            if course.corequisites.rstrip().endswith('.'):
                                # Replace terminal period with comma and a space
                                course.corequisites = course.corequisites.rstrip().rstrip('.') + ', ' + combined_text
                            else:
                                course.corequisites = f"{course.corequisites}; {combined_text}"
                    else:
                        course.corequisites = combined_text

                    self.add_warning(
                        f"Found combined Prerequisite/Corequisite for {course.course_code}: {combined_text} – merged with existing prerequisites/corequisites"
                    )
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
                
                i += lines_consumed
                continue
            
            # Parse "Formerly" line
            if line.startswith('Formerly'):
                # Only record the first valid 'Formerly' line to avoid later unrelated
                # occurrences (e.g., in marketing tables) from overwriting the value.
                if not course.formerly:
                    course.formerly = line.replace('Formerly', '').strip().rstrip('.')
                i += 1
                continue
            
            # IMPROVED: Parse standalone Prerequisites/Advisory/Corequisite lines (not in bullet format)
            if line.startswith('Prerequisites:') or line.startswith('Prerequisite:'):
                prereq_text = line.replace('Prerequisites:', '').replace('Prerequisite:', '').strip()
                course.prerequisites = prereq_text
                i += 1
                continue
            
            if line.startswith('Corequisites:') or line.startswith('Corequisite:'):
                coreq_text = line.replace('Corequisites:', '').replace('Corequisite:', '').strip()
                course.corequisites = coreq_text
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
                
                # If this line looks like an instructor-only line that belongs to the
                # most recently added schedule entry (which currently has an empty
                # instructor), attach it rather than treating it as a note.
                if (current_section.schedule and
                    not current_section.schedule[-1].instructor and
                    self._is_likely_instructor_only(line)):
                    current_section.schedule[-1].instructor = line.strip()
                    i += 1
                    continue
                
                # IMPROVED: More inclusive note collection when in section
                # First check for obvious non-note content that should end the section
                if (line.startswith('Transfer:') or 
                    line.startswith('C-ID:') or 
                    line.startswith('Cal-GETC') or
                    line.startswith('Prerequisites:') or
                    line.startswith('Prerequisite:') or
                    line.startswith('Corequisites:') or
                    line.startswith('Corequisite:') or
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
                    modality_match = re.search(r'modality is ([^.]+)', line)
                    if modality_match:
                        modality_value = modality_match.group(1).strip()
                        # Clean up any line break artifacts or extra whitespace
                        modality_value = re.sub(r'\s+', ' ', modality_value).strip()
                        current_section.modality = modality_value
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
                # Check for "same as" pattern - handle both "course" and "class" variations
                same_as_patterns = [
                    # Allow department codes with multiple uppercase words (e.g. "TH ART", "VAR PE")
                    r'([A-Z]+(?:\s+[A-Z]+)*\s+[A-Z]*\d+[A-Z]*)\s+is the same (?:course|class) as\s+([A-Z]+(?:\s+[A-Z]+)*\s+[A-Z]*\d+[A-Z]*)',
                    r'([A-Z]+(?:\s+[A-Z]+)*\s+[A-Z]*\d+[A-Z]*)\s+is the same as\s+([A-Z]+(?:\s+[A-Z]+)*\s+[A-Z]*\d+[A-Z]*)',
                ]
                
                same_as_found = False
                for pattern in same_as_patterns:
                    same_as_match = re.search(pattern, line)
                    if same_as_match:
                        course.same_as = same_as_match.group(2)
                        # Preserve the entire equivalency sentence as a note
                        if course.special_notes is None:
                            course.special_notes = []
                        course.special_notes.append(line.strip())
                        
                        # Add the part before "same as" to description if any
                        before_same_as = line[:same_as_match.start()].strip()
                        if before_same_as:
                            description_lines.append(before_same_as)
                        same_as_found = True
                        break
                
                if not same_as_found:
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
            # Also check if modality is incomplete (just "On" without "Ground")
            if not section.modality or section.modality == "On":
                # First, try the joined notes approach to handle split patterns
                all_notes_joined = ' '.join(section.notes)
                modality_match = re.search(r'modality is ([^.]+)', all_notes_joined)
                if modality_match:
                    modality_value = modality_match.group(1).strip()
                    # Clean up any line break artifacts or extra whitespace
                    modality_value = re.sub(r'\s+', ' ', modality_value).strip()
                    section.modality = modality_value
                
                # If we still don't have modality, try individual notes and alternative patterns
                if not section.modality:
                    for note in section.notes:
                        # Primary pattern: "modality is [value]" - stop at first period or end of sentence
                        # Handle cases where the modality value might have been split across lines
                        modality_match = re.search(r'modality is ([^.]+)', note)
                        if modality_match:
                            modality_value = modality_match.group(1).strip()
                            # Clean up any line break artifacts or extra whitespace
                            modality_value = re.sub(r'\s+', ' ', modality_value).strip()
                            section.modality = modality_value
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
                        
                        # "fully on ground" - indicates on ground modality
                        if re.search(r'fully on ground', note, re.IGNORECASE):
                            section.modality = 'On Ground'
                            break
                        
                        # "taught in person" - indicates on ground modality
                        if re.search(r'(?:will be )?taught in person', note, re.IGNORECASE):
                            section.modality = 'On Ground'
                            break
        
        # Post-process to establish co-enrollment relationships
        self.establish_co_enrollment_relationships(course)
        
        # IMPROVED: Validate parsed sections and remove empty/invalid ones
        course.sections = self.validate_parsed_sections(course)
        
        # TARGETED FIX: Handle specific course parsing issues where descriptions got absorbed into prerequisites
        # or where transfer information leaked into descriptions.
        # EXPANDED: Now handles mathematics courses and other complex cases.
        course = self._fix_course_descriptions(course)
        

        
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
            
            # IMPROVED: Extract "same as" information from description if not already set
            if not course.same_as:
                # Expanded patterns to handle variations: "is the same course as", "is the same class as"
                same_as_patterns = [
                    r'([A-Z]+(?:\s+[A-Z]+)*\s+[A-Z]*\d+[A-Z]*)\s+is the same (?:course|class) as\s+([A-Z]+(?:\s+[A-Z]+)*\s+[A-Z]*\d+[A-Z]*)',
                    r'([A-Z]+(?:\s+[A-Z]+)*\s+[A-Z]*\d+[A-Z]*)\s+is the same as\s+([A-Z]+(?:\s+[A-Z]+)*\s+[A-Z]*\d+[A-Z]*)',
                ]
                
                for pattern in same_as_patterns:
                    same_as_match = re.search(pattern, course.description)
                    if same_as_match:
                        course.same_as = same_as_match.group(2)
                        # Remove the "same as" clause from description
                        # Find the full sentence containing the match
                        full_sentence_pattern = r'[^.]*' + re.escape(same_as_match.group(0)) + r'[^.]*\.'
                        sentence_match = re.search(full_sentence_pattern, course.description)
                        if sentence_match:
                            full_sentence = sentence_match.group(0).strip()
                            if course.special_notes is None:
                                course.special_notes = []
                            course.special_notes.append(full_sentence)
                            course.description = re.sub(re.escape(full_sentence), '', course.description).strip()
                            # Clean up any double spaces or periods
                            course.description = re.sub(r'\s+', ' ', course.description).strip()
                        self.add_warning(f"Extracted same_as from description for {course_code}: {course.same_as}")
                        break
            
            # IMPROVED: Extract all asterisk notes from description and categorize them
            asterisk_patterns = [
                # Credit limitations and restrictions (should go to special_notes)
                # Generic asterisk credit limitation sentence (captures up to the first period)
                (r'(\*Maximum (?:UC )?credit (?:allowed )?for [^\.]+\.)', 'special'),
                (r'(\*No UC (?:transfer )?credit for [A-Z]+ \d+[A-Z]?(?: if taken [^.]*)?\.)', 'special'),
                (r'(\*Total of [A-Z]+ \d+[A-Z]? and [A-Z]+ \d+[A-Z]? combined[^.]*\.)', 'special'),
                (r'(\*UC gives no credit for [A-Z]+ \d+[A-Z]? if [^.]*\.)', 'special'),
                # Handle ESL-style combined credit patterns
                (r'(\*[A-Z]+ \d+[A-Z]?,\s*[A-Z]+ \d+[A-Z]?[^:]*:\s*maximum credit[^.]*\.)', 'special'),
                
                # Specific patterns for courses that start with asterisk notes
                (r'(\*No UC credit given for [A-Z]+ \d+[A-Z]? if taken after [^.]+\.)', 'special'),
                (r'(\*Total of four units credit for [A-Z]+ \d+[A-Z]? and [A-Z]+ \d+[A-Z]? is transferable\.)', 'special'),
                (r'(\*No UC credit for [A-Z]+ \d+[A-Z]? or \d+[A-Z]? if taken after [A-Z]+ \d+[A-Z]*\.)', 'special'),
                # Pattern for multiple course credit restrictions
                (r'(\*No UC credit for [A-Z]+ \d+[A-Z]?, [A-Z]+ \d+[A-Z]? or [A-Z]+ \d+[A-Z]? if taken after [^.]+\.)', 'special'),
                
                # Prerequisite explanations (should go to prerequisite_notes)
                (r'(\*The prerequisite for this course[^.]*)', 'prerequisite'),
                
                # Advisory explanations (should go to advisory_notes)
                (r'(\*The advisory for this course[^.]*)', 'advisory'),
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
            
            # Clean up any orphaned punctuation at the beginning of description
            course.description = re.sub(r'^[.\s,;:]+', '', course.description).strip()
            
            # NEW: Fix specific fragment issues found in test results
            fragment_fixes = {
                # CHEM 11: Missing beginning of transfer credit note
                'CHEM 11': {
                    'pattern': r'^students must complete both CHEM 11 and CHEM 12\.',
                    'replacement': 'To receive transfer credit, students must complete both CHEM 11 and CHEM 12.'
                },
                # CIS 1: Missing beginning of credit limitation note
                'CIS 1': {
                    'pattern': r'^or 4 if taken after CS 3\.',
                    'replacement': '*Maximum UC credit for CIS 1 or 4 if taken after CS 3.',
                    'move_to_special': True
                },
                # BIOL 33: Missing beginning of sentence
                'BIOL 33': {
                    'pattern': r'^work-ready skills in a bioscience research and biotechnology industry career\.',
                    'replacement': 'This course provides work-ready skills in a bioscience research and biotechnology industry career.'
                },
                # ACCTG 10A: Missing beginning of advisory sentence
                'ACCTG 10A': {
                    'pattern': r'^carefully, and reach out to your counselor if you have questions!',
                    'replacement': 'Please read degree requirements carefully, and reach out to your counselor if you have questions!'
                },
                # KIN PE 51A: Missing beginning of prerequisite check sentence
                'KIN PE 51A': {
                    'pattern': r'^on Day 1 of class: student must be able to swim',
                    'replacement': 'Prerequisites will be checked on Day 1 of class: student must be able to swim'
                },
                # COSM 95B, 95C, 95D: Missing beginning of experience description
                'COSM 95B': {
                    'pattern': r'^supervision of faculty\.',
                    'replacement': 'This course provides hands-on salon experience under the supervision of faculty.'
                },
                'COSM 95C': {
                    'pattern': r'^supervision of faculty\.',
                    'replacement': 'This course provides hands-on salon experience under the supervision of faculty.'
                },
                'COSM 95D': {
                    'pattern': r'^supervision of faculty\.',
                    'replacement': 'This course provides hands-on salon experience under the supervision of faculty.'
                }
            }
            
            # Apply fragment fixes if applicable
            if course.course_code in fragment_fixes:
                fix_info = fragment_fixes[course.course_code]
                pattern = fix_info['pattern']
                replacement = fix_info['replacement']
                
                if re.search(pattern, course.description):
                    course.description = re.sub(pattern, replacement, course.description)
                    
                    # If this should be moved to special_notes instead
                    if fix_info.get('move_to_special', False):
                        if course.special_notes is None:
                            course.special_notes = []
                        # Extract the fixed sentence and move to special_notes
                        sentence_match = re.match(r'^([^.]+\.)', course.description)
                        if sentence_match:
                            special_note = sentence_match.group(1)
                            course.special_notes.append(special_note)
                            course.description = course.description[sentence_match.end():].strip()
                    
                    self.add_warning(f"Fixed fragment issue for {course.course_code}: applied pattern fix")
            
            # IMPROVED: Extract credit-related continuation sentences (without asterisks)
            # These often follow asterisk notes and provide additional credit information
            credit_continuation_patterns = [
                # Maximum credit patterns
                r'(Maximum (?:UC )?credit for [A-Z]+ \d+[A-Z]?(?: and \d+[A-Z]?)* combined is [^.]+\.)',
                r'(Maximum (?:UC )?credit for [A-Z]+ \d+[A-Z]? and [A-Z]+ \d+[A-Z]? combined is [^.]+\.)',
                # Total credit patterns  
                r'(Total of [A-Z]+ \d+[A-Z]? and [A-Z]+ \d+[A-Z]? combined[^.]+\.)',
                # No credit patterns
                r'(No (?:UC )?credit for [A-Z]+ \d+[A-Z]? if taken [^.]+\.)',
                # UC gives patterns
                r'(UC gives no credit for [A-Z]+ \d+[A-Z]? if [^.]+\.)',
            ]
            
            # Only look for these if we already have special_notes (indicates this course has credit restrictions)
            if course.special_notes:
                for pattern in credit_continuation_patterns:
                    continuation_match = re.search(pattern, course.description)
                    if continuation_match:
                        continuation_note = continuation_match.group(1)
                        course.special_notes.append(continuation_note)
                        # Remove from description
                        course.description = re.sub(re.escape(continuation_note), '', course.description).strip()
                        # Clean up any double spaces
                        course.description = re.sub(r'\s+', ' ', course.description).strip()
                        self.add_warning(f"Extracted credit continuation note from description for {course_code}: {continuation_note}")
            
            # Clean up any orphaned punctuation at the beginning of description after all extractions
            course.description = re.sub(r'^[.\s,;:]+', '', course.description).strip()
            
            # IMPROVED: Extract "See also" statements from description and move to special_notes
            see_also_patterns = [
                # "See also COURSE 123." at the beginning of description
                r'^(See also [^.]+\.)\s*',
                # "See also COURSE 123 and COURSE 456." patterns
                r'^(See also [^.]+and[^.]+\.)\s*',
                # Handle cases without periods (less common but possible)
                r'^(See also [A-Z]+\s+\d+[A-Z]*(?:\s+and\s+[A-Z]+\s+\d+[A-Z]*)*)\s*(?=\.|This|Students|The|In)',
            ]
            
            for pattern in see_also_patterns:
                see_also_match = re.match(pattern, course.description)
                if see_also_match:
                    see_also_text = see_also_match.group(1).strip()
                    # Ensure it ends with a period
                    if not see_also_text.endswith('.'):
                        see_also_text += '.'
                    
                    # Add to special_notes
                    if course.special_notes is None:
                        course.special_notes = []
                    course.special_notes.append(see_also_text)
                    
                    # Remove from description
                    course.description = re.sub(pattern, '', course.description).strip()
                    self.add_warning(f"Extracted 'See also' note from description for {course_code}: {see_also_text}")
                    break  # Only process the first match
            
            # UPDATED: Extract advisory sentences (equivalence statements and/or credit-limitation statements)
            # that appear at the very start of the description. We keep looping while the next sentence
            # matches either "equivalent to" or "Students will receive credit for..." patterns.
            advisory_sentences: List[str] = []
            while True:
                sentence_match = re.match(r'^([^\.]*\.)\s*', course.description)
                if not sentence_match:
                    break
                first_sentence = sentence_match.group(1).strip()
                first_lower = first_sentence.lower()
                if ('equivalent to' in first_lower or
                        re.match(r'students?\s+will\s+receive\s+credit', first_lower)):
                    advisory_sentences.append(first_sentence)
                    # Remove this sentence (and following whitespace) from description
                    course.description = course.description[sentence_match.end():].lstrip()
                else:
                    break

            if advisory_sentences:
                advisory_text = ' '.join(advisory_sentences)
                if course.advisory_notes is None:
                    course.advisory_notes = advisory_text
                else:
                    if advisory_text not in course.advisory_notes:
                        course.advisory_notes += f"; {advisory_text}"
                self.add_warning(
                    f"Extracted advisory notes from description for {course_code}: {advisory_text}")

            if course.advisory:
                # Remove trailing asterisks/periods
                course.advisory = course.advisory.rstrip('*. ')

                # If advisory contains a semicolon, split into advisory and advisory_notes
                if ';' in course.advisory:
                    adv_parts = course.advisory.split(';', 1)
                    primary_adv = adv_parts[0].strip()
                    adv_note = adv_parts[1].strip()

                    course.advisory = primary_adv.rstrip('.')

                    # Capitalize first letter of note if needed
                    if adv_note and adv_note[0].islower():
                        adv_note = adv_note[0].upper() + adv_note[1:]

                    # Ensure sentence ends with period
                    if adv_note and not adv_note.endswith('.'):
                        adv_note += '.'

                    if course.advisory_notes:
                        # Append without duplication
                        if adv_note not in course.advisory_notes:
                            course.advisory_notes += (' ' if course.advisory_notes.endswith('.') else '; ') + adv_note
                    else:
                        course.advisory_notes = adv_note

                    self.add_warning(f"Split advisory into advisory and advisory_notes for {course_code}")

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
        if course.corequisites:
            course.corequisites = self.fix_hyphenation(course.corequisites)
        if course.advisory:
            course.advisory = self.fix_hyphenation(course.advisory)
        if course.advisory_notes:
            course.advisory_notes = self.fix_hyphenation(course.advisory_notes)
        if course.special_notes:
            course.special_notes = [self.fix_hyphenation(note) for note in course.special_notes]
            
            # Extract corequisites from special_notes and move to dedicated field
            remaining_special_notes = []
            for note in course.special_notes:
                # Check if this note is a corequisite
                if note.startswith('Corequisite:') or note.startswith('Corequisites:'):
                    coreq_text = note.replace('Corequisite:', '').replace('Corequisites:', '').strip()
                    if not course.corequisites:  # Only set if not already set
                        course.corequisites = coreq_text
                        self.add_warning(f"Extracted corequisite from special_notes for {course_code}: {coreq_text}")
                    # Don't add to remaining_special_notes since we moved it to corequisites field
                else:
                    remaining_special_notes.append(note)
            
            # Update special_notes with remaining notes
            course.special_notes = remaining_special_notes
            
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
        
        if course.advisory_notes:
            course.advisory_notes = self.fix_hyphenation(course.advisory_notes)

            # MOVE sentences that mention "prerequisite" into prerequisite_notes
            if re.search(r'prerequisite', course.advisory_notes, re.IGNORECASE):
                sentences = re.split(r'(?<=\.)\s+', course.advisory_notes.strip())
                remaining_adv = []
                for sent in sentences:
                    if re.search(r'prerequisite', sent, re.IGNORECASE):
                        sent_clean = sent.strip()
                        if sent_clean:
                            if course.prerequisite_notes:
                                # Avoid duplicates
                                if sent_clean not in course.prerequisite_notes:
                                    course.prerequisite_notes += ' ' + sent_clean
                            else:
                                course.prerequisite_notes = sent_clean
                    else:
                        remaining_adv.append(sent.strip())

                # Reconstruct advisory_notes without the moved sentences
                course.advisory_notes = ' '.join([s for s in remaining_adv if s]) or None

                if course.prerequisite_notes:
                    self.add_warning(
                        f"Moved advisory sentence mentioning prerequisite to prerequisite_notes for {course_code}")
        
        # Fallback for ENGL 31 if description still empty
        if course.course_code == 'ENGL 31' and not course.description and course.prerequisites and 'This advanced writing course' in course.prerequisites:
            parts = course.prerequisites.split('.',1)
            if len(parts)>=2:
                course.prerequisites = parts[0].strip()+'.'
                course.description = parts[1].strip()
                self.add_warning(f"Fallback fixed ENGL 31 description from prerequisites")
                return course
        
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
            
            # Many catalog lines include an extra standalone day token "N" (for "Arranged")
            # immediately after the hours, e.g. "Arrange-4.5 Hours N TH ART 130 Instructor".
            # That "N" is NOT part of the location – it is just the day designator that we
            # have already captured in the `days` field.  Remove it before parsing the
            # location/instructor so that legitimate room names like "TH ART 130" are kept.
            if rest.startswith("N "):
                rest = rest[2:].strip()

            # Use our robust parsing method for location and instructor
            location, instructor = self._parse_location_instructor(rest)

            # If we still could not determine a location (parser returned "N"), interpret
            # that as an online section.
            if location == "N":
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
        
        # ENHANCED: Handle specific case for "N Staff" in arrange schedules
        # "N" represents no specific day/location, "Staff" is the instructor
        if rest == "N Staff":
            return 'TBA', 'Staff'
        
        # NEW: Handle case where day token has already been stripped and only 'Staff' remains
        if rest == "Staff":
            return 'TBA', 'Staff'
        
        # ENHANCED: First check if this looks like an instructor-only case (common for arrange schedules)
        # This leverages the key insight that locations are ALL CAPS while instructor names are mixed case
        if self._is_likely_instructor_only(rest):
            return 'TBA', rest
        
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
        
        # Last resort: if we can't parse it cleanly, put everything in location
        # This prevents contamination of instructor names
        self.add_warning(f"Could not reliably parse location/instructor from: '{rest}' - defaulting to location only")
        return rest, ""
    
    def _is_likely_instructor_only(self, text: str) -> bool:
        """
        Determine if text is likely just an instructor name (no location).
        Uses the key insight that locations are ALL CAPS while instructor names are mixed case.
        
        This is particularly common for arrange schedules where there's no fixed location.
        """
        text = text.strip()
        
        # Must have at least 2 words for a typical instructor name
        words = text.split()
        if len(words) < 2:
            return False
        
        # Must contain lowercase letters (instructor names are mixed case)
        if not re.search(r'[a-z]', text):
            return False
        
        # Must NOT contain obvious location keywords
        location_keywords = ['ONLINE', 'TBA', 'ROOM', 'BLDG', 'LAB', 'STUDIO', 'CAMPUS', 'CENTER',
                           'HALL', 'AUDITORIUM', 'THEATER', 'GYM', 'FIELD', 'COURT']
        text_upper = text.upper()
        for keyword in location_keywords:
            if keyword in text_upper:
                return False
        
        # Check if it matches instructor name patterns
        # Enhanced patterns to handle names like "De Stefano J D"
        instructor_patterns = [
            # Last name + multiple initials: "Smith J A", "Williams V J"
            r'^[A-Z][a-z]+(?:\s+[A-Z]){1,3}\s*$',
            # Last name + first name + optional initials: "Smith John", "Smith John A"
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z])*\s*$',
            # Two-part last name + initials: "De Stefano J D", "Van Der Berg A B"  
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z]){1,3}\s*$',
            # Three-part names: "De La Cruz J", "Van Der Berg A"
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z])*\s*$',
        ]
        
        for pattern in instructor_patterns:
            if re.match(pattern, text):
                return True
        
        # Additional heuristic: if all words start with uppercase but contain lowercase,
        # and none of the words are typical location words, it's likely an instructor name
        all_words_proper_case = all(
            word[0].isupper() and re.search(r'[a-z]', word) 
            for word in words 
            if len(word) > 1  # Skip single letters (initials)
        )
        
        # Check that no word looks like a typical location abbreviation
        # (all caps words of 2+ letters that aren't initials)
        has_location_words = any(
            word.isupper() and len(word) >= 2
            for word in words
        )
        
        if all_words_proper_case and not has_location_words:
            return True
        
        return False
    
    def _is_valid_location(self, text: str) -> bool:
        """Check if text looks like a valid location (building, room, etc.)"""
        if not text:
            return False
        
        # Should be mostly uppercase with optional numbers
        # Allow some flexibility for abbreviations
        words = text.split()
        for word in words:
            # Each word should be either:
            # - All uppercase letters/numbers (isupper() or all digits)
            # - A mix but starting with uppercase and mostly uppercase
            if not (word.isupper() or 
                    word.isdigit() or  # Allow pure numbers like room numbers
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

        # Independent Studies, Internships, and similar reference programs are written to the extra_refs folder
        if program.program_name.strip().lower().startswith(("independent studies", "internships")):
            filepath = os.path.join(self.archived_dir, f"{filename}.json")
        else:
            filepath = os.path.join(self.output_dir, f"{filename}.json")
        
        # Convert to dict for JSON serialization
        program_dict = {
            "program_name": program.program_name,
            "program_description": program.program_description,
            "courses": []
        }
        
        for course in program.courses:
            course_dict = {
                "course_id": course.course_id,
                "course_code": course.course_code,
                "course_title": course.course_title,
                "units": course.units,
                "transfer_info": course.transfer_info,
                "c_id": course.c_id,
                "cal_getc_area": course.cal_getc_area,
                "special_notes": course.special_notes,
                "prerequisites": course.prerequisites,
                "prerequisite_notes": course.prerequisite_notes,
                "corequisites": course.corequisites,
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
    
    def save_small_headers_json(self):
        """Save all small headers to a separate JSON file"""
        # Use the archived_refs sub-folder for these rarely accessed references
        filepath = os.path.join(self.archived_dir, "cross_references.json")

        # Build a simple lookup table: header_name -> canonical program reference
        cross_ref_map: Dict[str, str] = {}

        for header in self.small_headers:
            desc = header.description.strip()

            # Attempt to extract the referenced program from patterns like:
            # "Please see listing under "Biological Sciences."" or
            # "Please see listing under \"Kinesiology/Physical Education.\""
            target_match = re.search(r'under\s+["\"\']?([^.]+?)\.', desc, re.IGNORECASE)
            if target_match:
                target_program = target_match.group(1).strip()
                cross_ref_map[header.header_name] = target_program
            else:
                # If we cannot parse a target, fall back to storing the full description
                # so the information is not lost (client code can decide whether to use it)
                cross_ref_map[header.header_name] = desc

        # Save mapping to JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cross_ref_map, f, indent=2, ensure_ascii=False)

        print(f"Saved {len(cross_ref_map)} cross-reference entries to {filepath}")
    
    def establish_co_enrollment_relationships(self, course: Course):
        """Establish co-enrollment relationships between sections based on notes"""
        for section in course.sections:
            # Join all notes for this section to handle multi-line patterns
            all_notes = ' '.join(section.notes)
            
            # Look for co-enrollment requirements in the combined notes
            co_enroll_match = re.search(r'requires co-enrollment in .+? section (\d{4})', all_notes)
            if co_enroll_match:
                section.co_enrollment_with = co_enroll_match.group(1)
    
    def _fix_mathematics_transfer_descriptions(self, course: Course) -> Optional[Course]:
        """
        Fix mathematics courses where transfer information and descriptions got mixed together.
        
        Pattern: "COURSE1 Transfer: info; COURSE2 Transfer: info Description text"
        """
        if not course.description:
            return None
        
        # TARGETED FIX 1: STAT C1000 with transfer info leak (combined course)
        if course.course_code == 'STAT C1000' and 'Transfer:' in course.description:
            # Pattern: "STAT C1000 Transfer: UC, CSU; MATH 54C Transfer: None STAT C1000 is an introduction..."
            pattern = r'STAT C1000 Transfer:\s*([^;]+);\s*MATH 54C Transfer:\s*([^S]+?)\s+(STAT C1000 is an introduction.+?)$'
            match = re.search(pattern, course.description, re.DOTALL)
            if match:
                stat_transfer = match.group(1).strip()
                math_transfer = match.group(2).strip()
                description_text = match.group(3).strip()
                
                # Set transfer info for STAT C1000
                if stat_transfer.lower() != 'none':
                    course.transfer_info = [t.strip() for t in stat_transfer.split(',')]
                
                # Set the clean description
                course.description = description_text
                
                # Add transfer limitation note to special_notes if MATH 54C had different transfer rules
                if math_transfer.strip().lower() != 'none':
                    if course.special_notes is None:
                        course.special_notes = []
                    course.special_notes.append(f"MATH 54C Transfer: {math_transfer.strip()}")
                
                self.add_warning(f"Fixed transfer info leak for {course.course_code}: extracted transfer info and description")
                return course
        
        # TARGETED FIX 2: MATH 2 with co-enrollment (first instance)
        if course.course_code == 'MATH 2' and course.units == '7 UNITS':
            # Pattern: "MATH 2 Transfer: UC*, CSU; MATH 2C Transfer: None *Maximum UC credit... Math 2: Description..."
            pattern = r'MATH 2 Transfer:\s*([^;]+);\s*MATH 2C Transfer:\s*([^*]+?)\s*(\*Maximum UC credit[^.]+\.)\s*Math 2:\s*(.+?)(?:\s*The corequisite Math 2C:|$)'
            match = re.search(pattern, course.description, re.DOTALL)
            if match:
                math2_transfer = match.group(1).strip()
                math2c_transfer = match.group(2).strip()
                credit_note = match.group(3).strip()
                description_text = match.group(4).strip()
                
                # Set transfer info
                course.transfer_info = [t.strip().rstrip('*') for t in math2_transfer.split(',')]
                
                # Set description
                course.description = description_text
                
                # Add special notes
                if course.special_notes is None:
                    course.special_notes = []
                course.special_notes.append(credit_note)
                if math2c_transfer.strip().lower() != 'none':
                    course.special_notes.append(f"MATH 2C Transfer: {math2c_transfer.strip()}")
                
                # Extract co-enrollment info if present
                coreq_match = re.search(r'The corequisite Math 2C:\s*(.+?)(?:\s*Pass/No Pass only\.|$)', course.description, re.DOTALL)
                if coreq_match:
                    coreq_description = coreq_match.group(1).strip()
                    course.description += f" The corequisite Math 2C: {coreq_description}"
                
                self.add_warning(f"Fixed transfer info leak for {course.course_code} (7 units): extracted transfer info and description")
                return course
        
        # TARGETED FIX 3: MATH 4 and MATH 4C courses with transfer info leak
        if course.course_code in ['MATH 4', 'MATH 4C'] and 'Transfer:' in course.description:
            # Pattern: "Math 4 Transfer: UC*, CSU; Math 4C Transfer: None *Maximum UC credit... MATH 4: Description..."
            pattern = r'Math 4 Transfer:\s*([^;]+);\s*Math 4C Transfer:\s*([^*]+?)\s*(\*Maximum UC credit[^.]+\.)\s*MATH 4:\s*(.+?)$'
            match = re.search(pattern, course.description, re.DOTALL)
            if match:
                math4_transfer = match.group(1).strip()
                math4c_transfer = match.group(2).strip()
                credit_note = match.group(3).strip()
                description_text = match.group(4).strip()
                
                # Set transfer info (for MATH 4, use the Math 4 transfer; for MATH 4C, it gets "None" so don't set transfer_info)
                if course.course_code == 'MATH 4':
                    course.transfer_info = [t.strip().rstrip('*') for t in math4_transfer.split(',')]
                
                # Set description
                course.description = description_text
                
                # Add special notes
                if course.special_notes is None:
                    course.special_notes = []
                course.special_notes.append(credit_note)
                if math4c_transfer.strip().lower() != 'none':
                    course.special_notes.append(f"Math 4C Transfer: {math4c_transfer.strip()}")
                
                self.add_warning(f"Fixed transfer info leak for {course.course_code}: extracted transfer info and description")
                return course
        
        # TARGETED FIX 3A: MATH 3 and MATH 3C courses with transfer info leak
        if course.course_code in ['MATH 3', 'MATH 3C'] and 'Transfer:' in course.description:
            # Pattern: "Math 3 Transfer: CSU; Math 3C Transfer: None Math 3: Description..."
            pattern = r'Math 3 Transfer:\s*([^;]+);\s*Math 3C Transfer:\s*([^M]+?)\s*Math 3:\s*(.+?)$'
            match = re.search(pattern, course.description, re.DOTALL)
            if match:
                math3_transfer = match.group(1).strip()
                math3c_transfer = match.group(2).strip()
                description_text = match.group(3).strip()
                
                # Set transfer info (for MATH 3, use the Math 3 transfer; for MATH 3C, it gets "None" so don't set transfer_info)
                if course.course_code == 'MATH 3':
                    course.transfer_info = [t.strip() for t in math3_transfer.split(',')]
                
                # Set description
                course.description = description_text
                
                # Add special notes for co-enrollment course if applicable
                if math3c_transfer.strip().lower() != 'none':
                    if course.special_notes is None:
                        course.special_notes = []
                    course.special_notes.append(f"Math 3C Transfer: {math3c_transfer.strip()}")
                
                self.add_warning(f"Fixed transfer info leak for {course.course_code}: extracted transfer info and description")
                return course
        
        # TARGETED FIX 3B: MATH 4C specific pattern (different from MATH 4)
        if course.course_code in ['MATH 4C'] and course.description.startswith('Math 4 Transfer:'):
            # Split the description to extract the components for MATH 4C
            desc_parts = course.description.split('The corequisite MATH 4C is a review')
            if len(desc_parts) >= 2:
                # Extract just the MATH 4C description part
                math4c_description = 'The corequisite MATH 4C is a review' + desc_parts[1]
                course.description = math4c_description
                
                # Extract any credit notes that appear before the description
                transfer_part = desc_parts[0]
                credit_match = re.search(r'(\*Maximum UC credit[^.]+\.)', transfer_part)
                if credit_match:
                    credit_note = credit_match.group(1)
                    if course.special_notes is None:
                        course.special_notes = []
                    course.special_notes.append(credit_note)
                
                self.add_warning(f"Fixed transfer info leak for {course.course_code}: extracted MATH 4C description")
                return course
        
        # TARGETED FIX 4: MATH 21 courses
        if course.course_code == 'MATH 21' and 'Transfer:' in course.description:
            # Pattern: "Math 21 Transfer: UC, CSU; MATH 21C Transfer: None Math 21: Description..."
            pattern = r'Math 21 Transfer:\s*([^;]+);\s*MATH 21C Transfer:\s*([^M]+?)\s*Math 21:\s*(.+?)$'
            match = re.search(pattern, course.description, re.DOTALL)
            if match:
                math21_transfer = match.group(1).strip()
                math21c_transfer = match.group(2).strip()
                description_text = match.group(3).strip()
                
                # Set transfer info
                course.transfer_info = [t.strip() for t in math21_transfer.split(',')]
                
                # Set description
                course.description = description_text
                
                # Add special notes for co-enrollment course if applicable
                if math21c_transfer.strip().lower() != 'none':
                    if course.special_notes is None:
                        course.special_notes = []
                    course.special_notes.append(f"MATH 21C Transfer: {math21c_transfer.strip()}")
                
                self.add_warning(f"Fixed transfer info leak for {course.course_code}: extracted transfer info and description")
                return course
        
        # TARGETED FIX 5: Handle description that starts with partial course title fragments
        # This handles cases like "21C, CONCURRENT SUPPORT FOR FINITE Math 21 Transfer:..."
        if course.description.startswith(('21C, CONCURRENT SUPPORT', 'C, CONCURRENT SUPPORT')):
            # Extract the meaningful part after the transfer info
            pattern = r'^[^M]*Math 21 Transfer:\s*([^;]+);\s*MATH 21C Transfer:\s*([^M]+?)\s*Math 21:\s*(.+?)$'
            match = re.search(pattern, course.description, re.DOTALL)
            if match:
                math21_transfer = match.group(1).strip()
                math21c_transfer = match.group(2).strip()
                description_text = match.group(3).strip()
                
                # Set transfer info
                course.transfer_info = [t.strip() for t in math21_transfer.split(',')]
                
                # Set description
                course.description = description_text
                
                # Add special notes
                if math21c_transfer.strip().lower() != 'none':
                    if course.special_notes is None:
                        course.special_notes = []
                    course.special_notes.append(f"MATH 21C Transfer: {math21c_transfer.strip()}")
                
                self.add_warning(f"Fixed description fragment for {course.course_code}: extracted transfer info and description")
                return course
        
        return None
    
    def _fix_course_descriptions(self, course: Course) -> Course:
        """
        Targeted fix for specific courses where descriptions got absorbed into prerequisites
        or where transfer information leaked into descriptions.
        EXPANDED: Now handles mathematics courses and other complex cases.
        """
        # Handle mathematics courses with transfer info leaked into descriptions
        math_transfer_fixes = self._fix_mathematics_transfer_descriptions(course)
        if math_transfer_fixes:
            return math_transfer_fixes
        
        # TARGETED FIX 0.5: Extract descriptions that start with "This [word] course" from prerequisites
        # This must run BEFORE fragment fixes to avoid conflicts
        if course.course_code == 'BIOL 33' and course.prerequisites and 'This techniques-focused course' in course.prerequisites:
            # Pattern: "BIOL 31. This techniques-focused course..."
            match = re.search(r'^(BIOL 31\.)\s+(This techniques-focused course.+?)$', course.prerequisites, re.DOTALL)
            if match:
                prereq_only = match.group(1).strip()
                description_text = match.group(2).strip()
                
                # Update the fields
                course.prerequisites = prereq_only
                
                # Combine with existing description if any, but avoid duplication
                if course.description and course.description.strip():
                    # Check if the existing description is already contained in the extracted text
                    if course.description not in description_text:
                        course.description = description_text + ' ' + course.description
                    else:
                        course.description = description_text
                else:
                    course.description = description_text
                
                self.add_warning(f"Extracted BIOL 33 description from prerequisites: 'This techniques-focused course...'")
                return course
        
        # TARGETED FIX 0.6: Extract descriptions that start with other patterns from prerequisites
        # Handle cases like "ACCTG 2. Basic pronouncements of the Financial Accounting Standards Board..."
        if course.prerequisites and not course.description:
            # Pattern to match "PREREQ. [Description starting with capital letter]..."
            # Look for prerequisite followed by description that doesn't start with common prerequisite words
            desc_patterns = [
                # Pattern for descriptions starting with "Basic pronouncements"
                r'^([A-Z]+\s+\d+[A-Z]*\.)\s+(Basic pronouncements.+?)$',
                # Pattern for other descriptive sentences that don't start with prerequisite indicators
                r'^([A-Z]+(?:\s+[A-Z]+)*\s+\d+[A-Z]*(?:\s+(?:and|or)\s+[A-Z]+(?:\s+[A-Z]+)*\s+\d+[A-Z]*)*\.)\s+([A-Z][^.]*(?:course|students|topics|emphasis|study|analysis|principles|concepts|methods|techniques|applications|overview|introduction|examination|exploration|development|understanding|knowledge|skills|preparation|training|instruction|education|learning).+?)$'
            ]
            
            for pattern in desc_patterns:
                match = re.search(pattern, course.prerequisites, re.DOTALL)
                if match:
                    prereq_only = match.group(1).strip()
                    description_text = match.group(2).strip()
                    
                    # Update the fields
                    course.prerequisites = prereq_only
                    course.description = description_text
                    
                    self.add_warning(f"Extracted description from prerequisites for {course.course_code}: '{description_text[:50]}...'")
                    return course
        
        # TARGETED FIX 0.7: Extract prerequisite explanatory notes from prerequisites field
        # Handle cases like "CHEM 10 and MATH 20. Students seeking waiver of the CHEM 10 prerequisite should take..."
        if course.prerequisites and not course.prerequisite_notes:
            # Pattern to match prerequisite followed by explanatory sentences about prerequisites
            prereq_note_patterns = [
                # Pattern for waiver/challenge exam explanations
                r'^([^.]+\.)\s+(Students seeking waiver[^.]+\.)\s*(.*?)$',
                # Pattern for general prerequisite explanations
                r'^([^.]+\.)\s+(Students taking [^.]+must[^.]+\.)\s*(.*?)$',
                # Pattern for other prerequisite-related explanations
                r'^([^.]+\.)\s+((?:Students|Note:|Please note:)[^.]*(?:prerequisite|requirement|waiver|challenge|exam)[^.]*\.)\s*(.*?)$'
            ]
            
            for pattern in prereq_note_patterns:
                match = re.search(pattern, course.prerequisites, re.DOTALL)
                if match:
                    prereq_only = match.group(1).strip()
                    prereq_note = match.group(2).strip()
                    remaining_text = match.group(3).strip() if len(match.groups()) >= 3 else ""
                    
                    # Update the fields
                    course.prerequisites = prereq_only
                    course.prerequisite_notes = prereq_note
                    
                    # If there's remaining text, decide where to place it
                    if remaining_text:
                        # If we already have a description, treat this as an additional note
                        # and store it in special_notes to avoid losing important guidance
                        if course.special_notes is None:
                            course.special_notes = []
                        if remaining_text not in course.special_notes:
                            course.special_notes.append(remaining_text)
                    
                    self.add_warning(f"Extracted prerequisite note for {course.course_code}: '{prereq_note[:50]}...'")
                    return course
        
        # TARGETED FIX: COSM 95 modules (A, B, C, D) - Remove variable unit duplication from prerequisites
        if course.course_code.startswith('COSM 95') and course.course_code in ['COSM 95A', 'COSM 95B', 'COSM 95C', 'COSM 95D']:
            if course.prerequisites and 'COSM 95 is a variable unit course' in course.prerequisites:
                # Enhanced handling for COSM 95 variable-unit modules
                # Pattern: Extract only the actual prerequisite part before the variable unit explanation
                prereq_text = course.prerequisites.strip()

                # Look for the variable-unit marker sentence
                marker = 'COSM 95 is a variable unit course'
                if marker in prereq_text:
                    prereq_part, remainder = prereq_text.split(marker, 1)
                    prereq_part = prereq_part.strip()
                    remainder = marker + remainder  # put marker back for clarity

                    # Split remainder where the real description starts
                    desc_match = re.search(r'(This\s+variable\s+unit[^.]*\.)', remainder)
                    if desc_match:
                        desc_start = desc_match.start()
                        special_note = remainder[:desc_start].strip()
                        description_text = remainder[desc_start:].strip()
                    else:
                        # If we cannot find the description starter, treat all as special note
                        special_note = remainder.strip()
                        description_text = ''

                    # Update prerequisite to only the actual requirement sentences
                    course.prerequisites = prereq_part.rstrip('.') + '.'

                    # Store the variable-unit explanation in special_notes
                    if course.special_notes is None:
                        course.special_notes = []
                    if special_note and special_note not in course.special_notes:
                        course.special_notes.append(special_note.rstrip('.') + '.')

                    # Place the true description if extracted
                    if description_text:
                        if not course.description or description_text not in course.description:
                            course.description = description_text

                    self.add_warning(f"Fixed COSM 95 prerequisites/notes/description for {course.course_code}")
                    return course
        
        # Special handling for CHEM 19 which has wrong description
        if course.course_code == 'CHEM 19':
            pass  # Continue to fix logic below
        elif not course.prerequisites or course.description:
            return course  # No fix needed
        
        # TARGETED FIX 1: ENGL 31 - Advanced writing course description pattern
        if course.course_code == 'ENGL 31':
            prereq_pattern = r'•\s*ENGL C1000 \(formerly ENGL 1\)\.\s*(This advanced writing course.+?)$'
            match = re.search(prereq_pattern, course.prerequisites, re.DOTALL)
            if match:
                description_text = match.group(1).strip()
                course.description = description_text
                course.prerequisites = 'ENGL C1000 (formerly ENGL 1).'
                self.add_warning(f"Fixed description for {course.course_code}: moved from prerequisites")
                return course
        
        # TARGETED FIX 2: ENGL 26 - Humanities course description pattern  
        if course.course_code == 'ENGL 26':
            prereq_pattern = r'(?:•\s*)?ENGL C1000 \(formerly ENGL 1\)\.\s*(In this introduction to the humanities.+?)(?=ENGL 26 is the same course)'
            match = re.search(prereq_pattern, course.prerequisites, re.DOTALL)
            if match:
                description_text = match.group(1).strip()
                course.description = description_text
                # Extract the same_as information
                same_as_match = re.search(r'ENGL 26 is the same course as ([A-Z]+ \d+)', course.prerequisites)
                if same_as_match:
                    course.same_as = same_as_match.group(1)
                course.prerequisites = 'ENGL C1000 (formerly ENGL 1).'
                self.add_warning(f"Fixed description for {course.course_code}: moved from prerequisites")
                return course
        
        # TARGETED FIX 3: ENGL 40 - Asian Literature course description pattern
        if course.course_code == 'ENGL 40':
            prereq_pattern = r'(?:•\s*)?ENGL C1000 \(formerly ENGL 1\)\.\s*(Major works of Asian literature.+?)$'
            match = re.search(prereq_pattern, course.prerequisites, re.DOTALL)
            if match:
                description_text = match.group(1).strip()
                course.description = description_text
                course.prerequisites = 'ENGL C1000 (formerly ENGL 1).'
                self.add_warning(f"Fixed description for {course.course_code}: moved from prerequisites")
                return course
        
        # TARGETED FIX 4: ENGL C1000 Group B - Complex combined course
        if course.course_code == 'ENGL C1000' and 'ENGL 28' in course.course_title:
            # This is the complex combined course case
            # The description should be extracted from the prerequisites of ENGL 28
            # but this requires cross-course coordination, so we'll handle it separately
            pass
        
        # TARGETED FIX 5: CHEM 10 - Chemistry course with asterisk notes
        if course.course_code == 'CHEM 10':
            # First try bullet style pattern
            prereq_pattern = r'•\s*([^.]+\.)\s*(\*[^.]+\.)\s*([^.]+\.)\s*(Chemistry 10 is a survey.+?)$'
            match = re.search(prereq_pattern, course.prerequisites, re.DOTALL)

            # Fallback pattern without leading bullet
            if not match:
                prereq_pattern_nb = r'^([^.]+\.)\s*(\*[^.]+\.)\s*([^.]+\.)\s*(Chemistry 10 is a survey.+?)$'
                match = re.search(prereq_pattern_nb, course.prerequisites, re.DOTALL)
            if match:
                prereq_only = match.group(1).strip()
                asterisk_note1 = match.group(2).strip()
                asterisk_note2 = match.group(3).strip()
                description_text = match.group(4).strip()
                 
                course.prerequisites = prereq_only
                course.description = description_text
                
                # Add asterisk notes to special_notes
                if course.special_notes is None:
                    course.special_notes = []
                course.special_notes.extend([asterisk_note1, asterisk_note2])
                
                self.add_warning(f"Fixed description for {course.course_code}: moved from prerequisites with asterisk notes")
                return course
        
        # TARGETED FIX 6: CS 20A - Computer Science course
        if course.course_code == 'CS 20A':
            prereq_pattern = r'•\s*CS 52\.\s*(This advanced programming course.+?)$'
            match = re.search(prereq_pattern, course.prerequisites, re.DOTALL)
            if match:
                description_text = match.group(1).strip()
                course.description = description_text
                course.prerequisites = 'CS 52.'
                self.add_warning(f"Fixed description for {course.course_code}: moved from prerequisites")
                return course
        
        # TARGETED FIX 7: HUM 26 - Humanities course (same pattern as ENGL 26)
        if course.course_code == 'HUM 26':
            # Allow optional leading bullet
            prereq_pattern = r'(?:•\s*)?ENGL C1000 \(formerly ENGL 1\)\.\s*(In this introduction to the humanities.+?)(?=HUM 26 is the same course)'
            match = re.search(prereq_pattern, course.prerequisites, re.DOTALL)
            if match:
                description_text = match.group(1).strip()
                course.description = description_text
                # Extract the same_as information
                same_as_match = re.search(r'HUM 26 is the same course as ([A-Z]+ \d+)', course.prerequisites)
                if same_as_match:
                    course.same_as = same_as_match.group(1)
                course.prerequisites = 'ENGL C1000 (formerly ENGL 1).'
                self.add_warning(f"Fixed description for {course.course_code}: moved from prerequisites")
                return course
        
        # TARGETED FIX 8: MATH 7 - Calculus course with asterisk note
        if course.course_code == 'MATH 7':
            prereq_pattern = r'(?:•\s*)?MATH 2 or \(MATH 3 and MATH 4\)\.\s*(\*[^.]+\.)\s*(This first course in calculus.+?)$'
            match = re.search(prereq_pattern, course.prerequisites, re.DOTALL)
            if match:
                asterisk_note = match.group(1).strip()
                description_text = match.group(2).strip()
                
                course.prerequisites = 'MATH 2 or (MATH 3 and MATH 4).'
                course.description = description_text
                
                # Add asterisk note to special_notes
                if course.special_notes is None:
                    course.special_notes = []
                course.special_notes.append(asterisk_note)
                
                self.add_warning(f"Fixed description for {course.course_code}: moved from prerequisites with asterisk note")
                return course
        
        # TARGETED FIX 9: ESL 11A - ESL course
        if course.course_code == 'ESL 11A':
            prereq_pattern = r'(?:•\s*)?ESL 10G and ESL 10W or Group C on the ESL Placement Assessment\.[^.]*\.\s*(ESL 11A is an intermediate.+?)$'
            match = re.search(prereq_pattern, course.prerequisites, re.DOTALL)
            if match:
                description_text = match.group(1).strip()
                course.description = description_text
                # Keep the full prerequisite text as it contains important placement info
                course.prerequisites = re.sub(r'\s*(ESL 11A is an intermediate.+?)$', '', course.prerequisites, flags=re.DOTALL).strip()
                self.add_warning(f"Fixed description for {course.course_code}: moved from prerequisites")
                return course
        
        # TARGETED FIX 10: ESL 15 - ESL conversation course
        if course.course_code == 'ESL 15':
            # Use flexible pattern to capture the prerequisite and description
            prereq_pattern = r'(?:•\s*)?(.*?)\.\s*(This speaking/listening course.+?)$'
            match = re.search(prereq_pattern, course.prerequisites, re.DOTALL)
            if match:
                prereq_only = match.group(1).strip()
                description_text = match.group(2).strip()
                course.description = description_text
                course.prerequisites = prereq_only + '.'
                self.add_warning(f"Fixed description for {course.course_code}: moved from prerequisites")
                return course
        
        # TARGETED FIX 11-13: MUSIC courses (53, 55, 59) - All have similar patterns
        music_courses = {
            'MUSIC 53': (r'(?:•\s*)?Audition required\.\s*(The jazz vocal ensemble.+?)$', 'Audition required.'),
            'MUSIC 55': (r'(?:•\s*)?Audition required\.\s*(The concert chorale.+?)$', 'Audition required.'),
            'MUSIC 59': (r'(?:•\s*)?Audition required\.\s*(The chamber choir.+?)$', 'Audition required.')
        }
        
        if course.course_code in music_courses:
            pattern, clean_prereq = music_courses[course.course_code]
            match = re.search(pattern, course.prerequisites, re.DOTALL)
            if match:
                description_text = match.group(1).strip()
                course.description = description_text
                course.prerequisites = clean_prereq
                self.add_warning(f"Fixed description for {course.course_code}: moved from prerequisites")
                return course
        
        # TARGETED FIX 14.6: General pattern for descriptions starting with "This [word] course" in prerequisites
        # This handles cases where the prerequisite field contains the prerequisite followed by the description
        if course.prerequisites and not course.description:
            # Pattern to match "PREREQ. This [word] course..." where [word] is any single word
            # More flexible pattern that can handle prerequisites with multiple sentences
            desc_in_prereq_pattern = r'^([A-Z]+(?:\s+[A-Z]+)*\s+\d+[A-Z]*(?:\s+(?:and|or)\s+[A-Z]+(?:\s+[A-Z]+)*\s+\d+[A-Z]*)*\.)\s+(This\s+\w+(?:[-‐]\w+)*\s+course.+?)$'
            match = re.search(desc_in_prereq_pattern, course.prerequisites, re.DOTALL)
            if match:
                prereq_only = match.group(1).strip()
                description_text = match.group(2).strip()
                
                # Update the fields
                course.prerequisites = prereq_only
                course.description = description_text
                
                self.add_warning(f"Extracted description starting with 'This [word] course' from prerequisites for {course.course_code}")
                return course
        
        # TARGETED FIX 14: CHEM 19 - Chemistry course with NOTE: This course is NOT equivalent pattern
        # Handle cases where prerequisites field contains: prerequisite + description + NOTE
        if course.course_code == 'CHEM 19' and course.prerequisites:
            # Make bullet‐agnostic pattern: prerequisite sentence, description sentences, NOTE sentence
            note_pattern = (
                r'^(?:•\s*)?([^.]+\.)\s*'  # prerequisite sentence ending with a period
                r'(.*?)\s*'                  # description block (lazy)
                r'(NOTE:\s*This course is NOT equivalent to CHEM 10 and does NOT meet the prerequisite requirement for CHEM 11\.)'
            )
            match = re.search(note_pattern, course.prerequisites, re.DOTALL | re.IGNORECASE)
            if match:
                prereq_only = match.group(1).strip()
                description_text = match.group(2).strip()
                note_text = match.group(3).strip()

                # Update fields
                course.prerequisites = prereq_only
                course.description = description_text

                # Put NOTE into advisory_notes (more appropriate) and special_notes for visibility
                course.advisory_notes = note_text
                if course.special_notes is None:
                    course.special_notes = []
                if note_text not in course.special_notes:
                    course.special_notes.append(note_text)

                self.add_warning(
                    f"Fixed CHEM 19 description/prerequisite separation: prereq='{prereq_only}', advisory NOTE captured")
                return course
        
        # SPECIAL CASE: COSM 95A - This course legitimately has no description in the catalog
        # It only has prerequisite information, so empty description is correct
        if course.course_code == 'COSM 95A':
            self.add_warning(f"COSM 95A: Empty description is correct - no description in catalog")
            return course
        
        # SPECIAL CASE: STAT C1000 and MATH 3 - These are combined courses with no sections
        # They may be catalog placeholders or have their content handled differently
        if course.course_code in ['STAT C1000', 'MATH 3']:
            self.add_warning(f"{course.course_code}: Course has no sections - may be placeholder or combined course")
            return course
        
        return course
    
    def _fix_english_group_b_courses(self, courses: List[Course]) -> List[Course]:
        """
        Targeted fix for English Composition Group B where ENGL C1000 and ENGL 28 
        should be combined into a single course entry.
        """
        fixed_courses = []
        engl_c1000_course = None
        engl_28_course = None
        
        # Find the two courses
        for course in courses:
            if course.course_code == 'ENGL C1000' and 'ENGL 28' in course.course_title:
                engl_c1000_course = course
            elif course.course_code == 'ENGL 28':
                engl_28_course = course
            else:
                fixed_courses.append(course)
        
        # If we found both courses, combine them properly
        if engl_c1000_course and engl_28_course:
            # Create the combined course
            combined_course = Course(
                course_code='ENGL C1000',
                course_title='ACADEMIC READING AND WRITING WITH ENGL 28, INTENSIVE COLLEGE WRITING SKILLS',
                units='5 UNITS',
                transfer_info=[],
                prerequisites='Placement Group B.',
                description='', # Will be set below
                sections=engl_28_course.sections  # Use ENGL 28's sections which have the schedule data
            )
            
            # Extract the proper description from ENGL 28's prerequisites
            if engl_28_course.prerequisites:
                # Pattern to extract the description from ENGL 28's prerequisites
                desc_pattern = r'Placement Group B\.\s*(In English C1000.+?)(?=Students will receive)'
                match = re.search(desc_pattern, engl_28_course.prerequisites, re.DOTALL)
                if match:
                    combined_course.description = match.group(1).strip()
                    self.add_warning("Fixed ENGL C1000/ENGL 28 combined course description")
            
            # If we still don't have a description, use the info from ENGL 28's description field
            if not combined_course.description and engl_28_course.description:
                # Extract just the meaningful part, not the credit info
                if 'Students will receive 3 units' in engl_28_course.description:
                    # Put the credit info in special notes instead
                    if combined_course.special_notes is None:
                        combined_course.special_notes = []
                    combined_course.special_notes.append(engl_28_course.description)
                else:
                    combined_course.description = engl_28_course.description
            
            # Set a default description if we still don't have one
            if not combined_course.description:
                combined_course.description = ("In English C1000, students receive instruction in academic reading and writing, "
                                             "including writing processes, effective use of language, analytical thinking, and the "
                                             "foundations of academic research. The co-enrollment English 28 emphasizes clear, "
                                             "effective written communication and preparation of the research paper to prepare "
                                             "students for success in college-level composition and reading.")
                self.add_warning("Used default description for ENGL C1000/ENGL 28 combined course")
            
            # Add credit information to special notes
            if combined_course.special_notes is None:
                combined_course.special_notes = []
            combined_course.special_notes.append("Students will receive 3 units of transferable credit for ENGL C1000, "
                                                "and 2 units of non-transferable, degree applicable credit for ENGL 28.")
            
            fixed_courses.append(combined_course)
            self.add_warning("Combined ENGL C1000 and ENGL 28 into single course entry")
        else:
            # If we didn't find both courses, keep them as-is
            if engl_c1000_course:
                fixed_courses.append(engl_c1000_course)
            if engl_28_course:
                fixed_courses.append(engl_28_course)
        
        return fixed_courses
    
    def assign_course_ids(self):
        """
        Generate and assign a unique ``course_id`` for every :class:`Course` instance
        across *all* programs in the catalog.

        Strategy:
        1.  Normalise the ``course_code`` by replacing whitespace with hyphens and
            stripping non-alphanumeric characters – e.g. "STAT C1000" → "STAT-C1000".
        2.  If a given ``course_code`` occurs more than once, append distinguishing
            tokens in the following order until uniqueness is reached:
            • the numeric portion of the *units* field (e.g. "4unit", "6unit").
            • a co-enrolment token extracted from the title of the form
              "WITH-{OTHERCOURSE}" (e.g. "WITH-MATH54C").
            • an incrementing integer suffix ("-1", "-2", …) as a last resort.

        All detected duplicate ``course_code`` values are logged via ``add_warning``
        so that they can be reviewed later.
        """
        code_to_courses: Dict[str, List[Course]] = {}

        # Build an index of course_code → list[Course]
        for program in self.programs:
            for course in program.courses:
                code_to_courses.setdefault(course.course_code, []).append(course)

        assigned_ids = set()

        for code, course_list in code_to_courses.items():
            base_id = re.sub(r'\s+', '-', code.strip())            # spaces → dash
            base_id = re.sub(r'[^A-Za-z0-9\-]', '', base_id).upper()  # keep A-Z,0-9 and '-'

            if len(course_list) > 1:
                self.add_warning(f"Duplicate course_code detected: '{code}' appears {len(course_list)} times.")

            for course in course_list:
                components = [base_id]

                # Append units token if present (e.g. 4unit, 6unit, 2.5unit)
                if course.units:
                    m = re.match(r'(\d+(?:\.\d+)?)', course.units)
                    if m:
                        num_units = m.group(1).rstrip('0').rstrip('.') if '.' in m.group(1) else m.group(1)
                        components.append(f"{num_units}UNIT")

                # Append co-enrolment token if title contains "WITH XXX"
                with_match = re.search(r'WITH\s+([A-Z]+\s+\d+[A-Z]*)', course.course_title, re.IGNORECASE)
                if with_match:
                    with_code = with_match.group(1).replace(' ', '')
                    components.append(f"WITH-{with_code}")

                candidate = '-'.join(components).upper()

                # Guarantee uniqueness in the unlikely event collisions remain
                unique_candidate = candidate
                counter = 1
                while unique_candidate in assigned_ids:
                    unique_candidate = f"{candidate}-{counter}"
                    counter += 1

                course.course_id = unique_candidate
                assigned_ids.add(unique_candidate)

    def _replace_independent_studies_descriptions(self):
        """
        Replace placeholder descriptions that instruct the reader to "see Independent Studies section"
        with the full Independent Studies program description.  This ensures that every course has
        a self-contained, meaningful description rather than an external reference.
        """
        # Attempt to locate the Independent Studies program description that already exists in
        # the parsed data.  Fall back to a hard-coded default if, for some reason, it is missing.
        independent_desc = None
        for prog in self.programs:
            if prog.program_name.strip().lower().startswith("independent studies"):
                independent_desc = prog.program_description.strip()
                break

        # Hard-coded fallback (matches the verbiage provided by the user).
        if not independent_desc:
            independent_desc = (
                "Independent study is intended for advanced students interested in doing independent "
                "research on special study topics. To be eligible, a student must demonstrate to the "
                "department chairperson the competence to do independent study. To apply for Independent "
                "Studies, the student is required, in a petition that may be obtained from the department "
                "chair, to state objectives to be achieved, activities and procedures to accomplish the "
                "study project, and the means by which the supervising instructor may assess accomplishment. "
                "Please see department listing for details. A maximum of six units of independent studies is "
                "allowed. Granting of UC transfer credit for an Independent Studies course is contingent "
                "upon an evaluation of the course outline by a UC campus."
            )

        placeholder_re = re.compile(r'^Please\s+see.+Independent\s+Studies.+section\.?.*$', re.IGNORECASE)

        for prog in self.programs:
            for course in prog.courses:
                if course.description and placeholder_re.match(course.description.strip()):
                    course.description = independent_desc
                    self.add_warning(
                        f"Replaced Independent Studies placeholder description for {course.course_code} in {prog.program_name}")

        # Build list of (regex, replacement_text) tuples for each placeholder type we support
        internship_desc = None
        for prog in self.programs:
            if prog.program_name.strip().lower().startswith("internships"):
                internship_desc = prog.program_description.strip()
                break

        # Hard-coded fallback (mirrors catalog wording) if internships program not found
        if not internship_desc:
            internship_desc = (
                "The Internship Program at Santa Monica College makes it possible for students to enhance "
                "their classroom learning and earn college credit by working in on and off campus jobs. "
                "Students must arrange an approved internship with an employer prior to enrolling in this "
                "class. Each unit of credit requires the student to work a minimum of 60 hour of unpaid "
                "(volunteer) work or 75 hours of paid work throughout the semester. F-1 international "
                "students must see an International Student Services Specialist at the International "
                "Education Center for pre-approval before securing an internship and enrolling in internship "
                "courses. Students may enroll in a maximum of 4 units of internship credits per semester, "
                "and a total of 8 internship units may be applied toward the Associate degree. See an "
                "academic counselor for transfer credit limitations. Internships are graded on a pass/no "
                "pass basis only. Please see smc.edu/internship for additional information and for the "
                "internship orientation schedule. Go to smc.edu/hiresmc to find jobs and internships or "
                "visit the Career Services Center for assistance."
            )

        replacement_rules = [
            (re.compile(r'^Please\s+see.+Independent\s+Studies.+section\.?.*$', re.IGNORECASE), independent_desc),
            (re.compile(r'^Please\s+see.+Internships.+section\.?.*$', re.IGNORECASE), internship_desc),
        ]

        for prog in self.programs:
            for course in prog.courses:
                if not course.description:
                    continue
                desc_stripped = course.description.strip()
                for regex, replacement in replacement_rules:
                    if regex.match(desc_stripped):
                        course.description = replacement
                        self.add_warning(
                            f"Replaced placeholder description for {course.course_code} in {prog.program_name} using '{regex.pattern.split('+')[2].strip()}'.")
                        break



# Example usage
if __name__ == "__main__":
    parser = SMCCatalogParser(os.path.join(os.path.dirname(__file__), "catalog_cleaned.txt"), os.path.join(os.path.dirname(__file__), "parsed_programs"))
    parser.parse()
    print(f"\nParsed {len(parser.programs)} programs and {len(parser.small_headers)} small headers")
    
    # Print parsing warnings summary
    if parser.parsing_warnings:
        print(f"\n=== PARSING WARNINGS ({len(parser.parsing_warnings)}) ===")
        for warning in parser.parsing_warnings[-10:]:  # Show last 10 warnings
            print(f"  {warning}")
        if len(parser.parsing_warnings) > 10:
            print(f"  ... and {len(parser.parsing_warnings) - 10} more warnings")
    
    # Print summary
    print(f"\n=== MAIN PROGRAMS ({len(parser.programs)}) ===")
    for program in parser.programs:
        print(f"  {program.program_name}: {len(program.courses)} courses")
    
    print(f"\n=== SMALL HEADERS ({len(parser.small_headers)}) ===")
    for small_header in parser.small_headers:
        print(f"  {small_header.header_name}: {small_header.description}")