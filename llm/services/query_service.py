"""
TransferAI Query Service

This module provides services for processing and analyzing user queries.
It extracts information from raw queries and categorizes them by type.
"""

from typing import Dict, List, Any, Set, Optional, Tuple, Union
import re
import spacy

from llm.models.query import Query, QueryType

# Load spaCy model for NLP processing
nlp = spacy.load("en_core_web_sm")

class QueryService:
    """
    Service for processing and analyzing user queries.
    
    Extracts structured information from raw text queries and
    categorizes them by type for appropriate handling.
    """
    
    def normalize_course_code(self, code: str) -> str:
        """
        Normalize course codes to a standard format (e.g., 'cis-21ja:' → 'CIS 21JA').
        
        This function standardizes various course code formats to ensure consistent matching
        regardless of input format variations. It handles patterns like 'CIS21JA', 'MATH 2BH',
        'PHYS-4A', etc.
        
        Args:
            code: The course code string to normalize.
            
        Returns:
            A normalized course code in the format "DEPT NUM" (e.g., "CIS 22A").
            
        Examples:
            >>> normalize_course_code("cis-21ja:")
            'CIS 21JA'
            >>> normalize_course_code("MATH2BH")
            'MATH 2BH'
        """
        code = code.upper()
        code = re.sub(r"[^A-Z0-9]", "", code)  # Remove all non-alphanumerics

        # Match subject + number + up to 2 trailing letters (e.g. '21JA', '2BH')
        # Updated regex to handle longer department names (up to 8 characters)
        match = re.match(r"([A-Z]{2,8})(\d+[A-Z]{0,2})", code)
        if match:
            subject = match.group(1)
            number = match.group(2)
            return f"{subject} {number}"

        return code  # Fallback
        
    def extract_prefixes_from_docs(self, docs: List[Any], key: str) -> List[str]:
        """
        Extract course code prefixes (department codes) from document metadata.
        
        Analyzes document metadata to extract unique department prefixes (e.g., "CSE", "MATH")
        from course codes to help with course code identification in queries.
        
        Args:
            docs: List of documents containing metadata.
            key: The metadata key that contains course codes ("uc_course" or "ccc_courses").
            
        Returns:
            A sorted list of unique department prefixes found in the documents.
            
        Example:
            >>> extract_prefixes_from_docs(docs, "uc_course")
            ['BILD', 'CSE', 'MATH', 'PHYS']
        """
        prefixes = set()
        for doc in docs:
            values = doc.metadata.get(key, [])
            if isinstance(values, str):
                values = [values]
            for val in values:
                normalized = self.normalize_course_code(val)
                match = re.match(r"([A-Z]{2,6})\s\d+", normalized)
                if match:
                    prefixes.add(match.group(1))
        return sorted(prefixes)
    
    def extract_filters(
        self, 
        query_text: str, 
        uc_course_catalog: Optional[Set[str]] = None,
        ccc_course_catalog: Optional[Set[str]] = None
    ) -> Dict[str, List[str]]:
        """
        Extract UC and CCC course codes from a natural language query.
        
        Uses NLP and pattern matching to identify course codes in user queries, distinguishing
        between UC and CCC courses based on the provided course catalogs.
        
        Args:
            query_text: The user's natural language query.
            uc_course_catalog: Set of known UC course codes (e.g., "CSE 8A").
            ccc_course_catalog: Set of known CCC course codes (e.g., "CIS 22A").
            
        Returns:
            A dictionary with keys "uc_course" and "ccc_courses", each containing a sorted
            list of course codes extracted from the query.
            
        Example:
            >>> extract_filters("Does CIS 22A satisfy CSE 8A?", {"CSE 8A"}, {"CIS 22A"})
            {'uc_course': ['CSE 8A'], 'ccc_courses': ['CIS 22A']}
        """
        filters = {"uc_course": set(), "ccc_courses": set()}
        doc = nlp(query_text.upper())
        last_prefix = None

        # Process each token in the query
        for i, token in enumerate(doc):
            text = token.text.strip(",.?!")
            next_token = doc[i + 1].text.strip(",.?!") if i + 1 < len(doc) else None

            # Skip coordination words — preserve last prefix
            if text in {"AND", "OR", "WITH", "TO", "FOR"}:
                continue

            course = None

            # Full course (e.g., CSE 8A)
            if re.fullmatch(r"[A-Z]{2,5}", text) and next_token and re.fullmatch(r"\d+[A-Z]{0,2}", next_token):
                course = f"{text} {next_token}"
                last_prefix = text

            # Suffix only (e.g., '8B' after 'CSE')
            elif re.fullmatch(r"\d+[A-Z]{0,2}", text) and last_prefix:
                course = f"{last_prefix} {text}"

            else:
                continue

            # Determine if course is UC or CCC
            in_uc = course in (uc_course_catalog or set())
            in_ccc = course in (ccc_course_catalog or set())

            if in_uc and not in_ccc:
                filters["uc_course"].add(course)
            elif in_ccc and not in_uc:
                filters["ccc_courses"].add(course)
            elif in_uc and in_ccc:
                filters["ccc_courses"].add(course)

        return {
            "uc_course": sorted(filters["uc_course"]),
            "ccc_courses": sorted(filters["ccc_courses"])
        }
    
    def extract_reverse_matches(self, query: str, docs: List[Any]) -> List[Any]:
        """
        Find documents where any CCC course in the metadata appears in the user query.
        
        Performs a reverse lookup to find articulation documents where the CCC course
        codes mentioned in the document match courses mentioned in the query.
        
        Args:
            query: The user's query text.
            docs: List of articulation documents to search through.
            
        Returns:
            A list of matching documents where at least one CCC course appears in the query.
        """
        query_upper = query.upper()
        matches = []
        for doc in docs:
            ccc_list = doc.metadata.get("ccc_courses") or []
            for cc in ccc_list:
                if self.normalize_course_code(cc) in query_upper:
                    matches.append(doc)
                    break
        return matches

    def extract_group_matches(self, query: str, docs: List[Any]) -> List[Any]:
        """
        Find documents matching a group mentioned in the query (e.g., 'Group 3').
        
        Uses regex to detect group number references in queries and returns all documents
        belonging to that group.
        
        Args:
            query: The user's query text.
            docs: List of articulation documents to search through.
            
        Returns:
            A list of documents belonging to the group mentioned in the query.
        """
        group_match = re.search(r"\bgroup\s*(\d+)\b", query.lower())
        if not group_match:
            return []

        group_num = group_match.group(1).strip()
        return [doc for doc in docs if str(doc.metadata.get("group", "")).strip() == group_num]

    def extract_section_matches(self, query: str, docs: List[Any]) -> List[Any]:
        """
        Find documents matching a specific section within a group.
        
        Detects mentions like 'section A of group 2' and returns matching documents.
        
        Args:
            query: The user's query text.
            docs: List of articulation documents to search through.
            
        Returns:
            A list of documents belonging to the specific section of the group.
        """
        # Use a flexible pattern that looks for group number and section letter anywhere in the query
        # This will match formats like:
        # - "Group 3 Section C"
        # - "What's in Group 3 Section C"
        # - "Tell me about Section C of Group 3"
        q_lower = query.lower()
        
        # Look for group number
        group_match = re.search(r"group\s*(\d+)", q_lower)
        if not group_match:
            return []
        
        # Look for section letter
        section_match = re.search(r"section\s*([a-z])", q_lower)
        if not section_match:
            return []
            
        group_num = group_match.group(1)
        section_label = section_match.group(1).upper()
        
        results = []
        for doc in docs:
            doc_group = str(doc.metadata.get("group", "")).strip()
            doc_section = str(doc.metadata.get("section", "")).strip().upper()
            
            if doc_group == group_num and doc_section == section_label:
                results.append(doc)
                
        return results

    def split_multi_uc_query(self, query: str, uc_courses: List[str]) -> List[str]:
        """
        Split a multi-course query into individual queries for each UC course.
        
        Used for handling queries about multiple UC courses by creating focused sub-queries.
        
        Args:
            query: The original user query.
            uc_courses: List of UC courses detected in the query.
            
        Returns:
            List of modified queries, each focusing on a specific UC course.
        """
        return [f"{query.strip()} (focus on {uc})" for uc in uc_courses]

    def enrich_uc_courses_with_prefixes(self, matches: List[str], uc_prefixes: List[str]) -> List[str]:
        """
        Enrich course code matches with department prefixes where needed.
        
        Handles cases where only the course number is mentioned by applying the appropriate
        department prefix based on context. For example, "CSE 8A and 8B" becomes
        ["CSE 8A", "CSE 8B"].
        
        Args:
            matches: List of raw course code matches from the query.
            uc_prefixes: List of known UC department prefixes.
            
        Returns:
            List of enriched course codes with proper department prefixes.
        """
        enriched = []
        last_prefix = None

        for raw in matches:
            normalized = self.normalize_course_code(raw)
            parts = normalized.split()

            # Skip junk like 'AND', 'OR', etc.
            if len(parts) == 1 and not re.match(r"\d+[A-Z]{0,2}$", parts[0]):
                continue

            if len(parts) == 2:
                prefix, number = parts
                if prefix in uc_prefixes:
                    last_prefix = prefix
                    enriched.append(normalized)
                else:
                    # '15L' with no known prefix → try last seen prefix
                    if last_prefix and re.match(r"\d+[A-Z]{0,2}$", number):
                        enriched.append(f"{last_prefix} {prefix}")
            elif len(parts) == 1:
                # Pure number like '15L' → use last seen subject prefix
                if last_prefix:
                    enriched.append(f"{last_prefix} {parts[0]}")
            else:
                # Unexpected format — skip
                continue

        return enriched

    def find_uc_courses_satisfied_by(self, ccc_code: str, docs: List[Any]) -> List[Any]:
        """
        Find UC courses that can be satisfied by a specific CCC course.
        
        Searches through documents to find UC courses where the given CCC course
        appears in the articulation logic.
        
        Args:
            ccc_code: The CCC course code to search for.
            docs: List of articulation documents to search through.
            
        Returns:
            List of documents for UC courses satisfied by the given CCC course.
        """
        matched_docs = []
        for doc in docs:
            logic_block = doc.metadata.get("logic_block", {})
            if not logic_block or logic_block.get("no_articulation"):
                continue

            if self._logic_block_contains_ccc_course(logic_block, ccc_code):
                matched_docs.append(doc)

        return matched_docs

    def _logic_block_contains_ccc_course(self, logic_block: Dict[str, Any], target_ccc: str) -> bool:
        """
        Check if a specific CCC course appears in the articulation logic block.
        
        Searches through the logic block for the target CCC course code, handling
        both single courses and course groups.
        
        Args:
            logic_block: The articulation logic block to search.
            target_ccc: The CCC course code to look for.
            
        Returns:
            True if the course appears in the logic block, False otherwise.
        """
        norm = lambda s: self.normalize_course_code(s)

        for option in logic_block.get("options", []):
            for course in option.get("courses", []):
                if isinstance(course, list):  # AND group
                    if any(norm(c) == norm(target_ccc) for c in course):
                        return True
                elif isinstance(course, str):  # single course
                    if norm(course) == norm(target_ccc):
                        return True
        return False
    
    def determine_query_type(self, query: Query) -> QueryType:
        """
        Determine the type of a query.
        
        This method analyzes the query text and extracted filters to categorize
        the query into specific types for proper handling. It uses both exact
        pattern matching and keyword analysis to identify query intent.
        
        Args:
            query: The query to categorize
            
        Returns:
            The determined query type
        """
        query_lower = query.text.lower()
        
        # First check if we can determine the type from the filters
        if 'group' in query.filters and query.filters['group']:
            return QueryType.GROUP_REQUIREMENT
            
        # Check for course comparison queries - look for comparative patterns
        if 'uc_course' in query.filters and len(query.filters['uc_course']) >= 2:
            # Keywords indicating comparison
            comparison_keywords = [
                'same', 'similar', 'different', 'alike', 'equivalent',
                'compare', 'comparison', 'versus', 'vs', 'like', 'match',
                'require the same', 'both require', 'both need',
                'both accept', 'both satisfy'
            ]
            
            # Patterns for comparison queries
            comparison_patterns = [
                r'(?:same|similar|different)(?:\s+\w+)*\s+(?:as|to|from|than)',
                r'(?:compare|compared|comparing)(?:\s+\w+)*\s+(?:to|with)',
                r'(?:both|either|neither)(?:\s+\w+)*\s+(?:require|need|accept)',
                r'(?:match|matches|matching)(?:\s+\w+)*\s+(?:with|to)',
                r'(?:do|does)(?:\s+\w+)*\s+(?:require|need|accept)(?:\s+\w+)*\s+(?:same|similar|different)'
            ]
            
            # Check for comparison keywords
            if any(keyword in query_lower for keyword in comparison_keywords) or \
               any(re.search(pattern, query_lower) for pattern in comparison_patterns):
                return QueryType.COURSE_COMPARISON
                
        # Check for path completion queries - look for full path, complete requirement patterns
        if 'uc_course' in query.filters and query.filters['uc_course']:
            path_keywords = [
                'full path', 'complete path', 'complete requirement', 'finish requirement',
                'satisfy requirement', 'satisfy section', 'complete section',
                'entire path', 'one path', 'enough for', 'sufficient for'
            ]
            
            path_patterns = [
                r'(?:is|are|do|does)\s+.+\s+(?:one|a|the)\s+(?:full|complete|entire)\s+path',
                r'(?:is|are|do|does)\s+.+\s+(?:complete|satisfy|finish)\s+(?:the|a|one)\s+(?:requirement|section|path)',
                r'(?:is|are|do|does)\s+.+\s+(?:enough|sufficient)\s+(?:to|for|in)\s+(?:complete|satisfy)'
            ]
            
            if any(keyword in query_lower for keyword in path_keywords) or any(re.search(pattern, query_lower) for pattern in path_patterns):
                return QueryType.PATH_COMPLETION

        # COURSE VALIDATION CHECK (does X satisfy Y?)
        # Do this check before honors to ensure proper precedence
        if 'uc_course' in query.filters and 'ccc_courses' in query.filters:
            if len(query.filters['uc_course']) == 1 and len(query.filters['ccc_courses']) >= 1:
                validation_keywords = ['does', 'do', 'can', 'will', 'satisfy', 'meet', 'fulfill', 'equivalent']
                # If query contains both course types and any validation keyword, prioritize this as validation
                if any(keyword in query_lower for keyword in validation_keywords):
                    return QueryType.COURSE_VALIDATION
            
        # Check for honors query - specific honors requirement questions only
        honors_keywords = ['honors', 'honour', 'honor', 'h course', 'h version', 'h class', 'h-designated']
        if any(keyword in query_lower for keyword in honors_keywords):
            # Look for specific honors requirement question patterns
            honors_patterns = [
                r"(?:does|do|is|are).*(?:require|requires|need|needs).*honors",
                r"honors.*(?:require|required|necessity|needed)",
                r"(?:need|needs).*honors"
            ]
            
            # Only classify as HONORS_REQUIREMENT if it's specifically asking if honors is required
            if any(re.search(pattern, query_lower) for pattern in honors_patterns):
                return QueryType.HONORS_REQUIREMENT
        
        # Check for "has articulation" queries
        if 'uc_course' in query.filters and query.filters['uc_course'] and len(query.filters['uc_course']) == 1:
            articulation_keywords = ['articulation', 'has articulation', 'articulated', 'have articulation', 'any articulation']
            articulation_patterns = [
                r"(?:does|do|is|are|has|have)\s+\w+\s+(?:any|have|has)\s+articulation",
                r"(?:is|are)\s+\w+\s+articulated",
                r"(?:can|could)\s+\w+\s+(?:be|get)\s+articulated",
                r"(?:does|is)\s+there\s+(?:a|any)\s+(?:course|articulation)\s+for\s+\w+"
            ]
            
            if any(keyword in query_lower for keyword in articulation_keywords) or \
               any(re.search(pattern, query_lower) for pattern in articulation_patterns):
                return QueryType.COURSE_LOOKUP
        
        # Check for course lookup queries (which courses satisfy X?)
        # This pattern checks for various ways users ask about what courses satisfy a requirement
        lookup_patterns = [
            r"which\s+(?:\w+\s+)*courses?\s+(?:satisfy|fulfill|meet|complete|articulate\s+to|articulate\s+with|transfer\s+to|transfer\s+as)\s+(.+?)(?:\?|$|at)",
            r"what\s+(?:\w+\s+)*courses?\s+(?:satisfy|fulfill|meet|complete|articulate\s+to|articulate\s+with|transfer\s+to|transfer\s+as)\s+(.+?)(?:\?|$|at)",
            r"courses?\s+(?:that|which|to)\s+(?:satisfy|fulfill|meet|complete|articulate\s+to|articulate\s+with|transfer\s+to|transfer\s+as)\s+(.+?)(?:\?|$|at)",
            r"(?:satisfy|fulfill|meet|complete)\s+(.+?)(?:\s+with|$|\?)"
        ]
        
        # If query contains a lookup pattern and has a UC course filter, it's likely a COURSE_LOOKUP
        for pattern in lookup_patterns:
            if re.search(pattern, query_lower) and 'uc_course' in query.filters and query.filters['uc_course']:
                return QueryType.COURSE_LOOKUP
        
        # IMPROVED: Course lookup detection - prioritize "which courses satisfy X" type queries
        # This handles simple queries like "Which courses satisfy CSE 8B?" or "What satisfies CSE 11?"
        if ('uc_course' in query.filters and query.filters['uc_course'] and 
            ('ccc_courses' not in query.filters or not query.filters['ccc_courses'])):
            
            satisfy_keywords = ['satisfy', 'fulfil', 'fulfill', 'meet', 'complete', 'articulate', 'transfer', 'equivalent']
            question_starters = ['what', 'which', 'how', 'tell me', 'show me', 'list', 'find']
            
            # For general queries about satisfying a UC course, classify as COURSE_LOOKUP
            if any(keyword in query_lower for keyword in satisfy_keywords) or any(starter in query_lower for starter in question_starters):
                return QueryType.COURSE_LOOKUP
        
        # Check if query mentions a school and UC course, likely asking for articulation
        school_keywords = ['de anza', 'deanza', 'foothill', 'community college', 'ccc', 'college']
        if ('uc_course' in query.filters and query.filters['uc_course'] and 
            any(school in query_lower for school in school_keywords)):
            
            return QueryType.COURSE_LOOKUP
        
        # Check for course equivalency query (what does X satisfy?)
        if 'ccc_courses' in query.filters and len(query.filters['ccc_courses']) >= 1:
            if 'uc_course' not in query.filters or not query.filters['uc_course']:
                return QueryType.COURSE_EQUIVALENCY
            
        # If we can't determine the type, fall back to UNKNOWN
        return QueryType.UNKNOWN
