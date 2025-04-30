"""
TransferAI Course Comparison Query Handler

This module implements a handler for course comparison queries, which analyze
and compare requirements between different UC courses.
"""

from typing import Optional, Dict, Any, List, Set, Tuple
import re
import logging

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.base import QueryHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.matching_service import MatchingService
from llm.services.articulation_facade import ArticulationFacade

# Set up logger
logger = logging.getLogger(__name__)


class CourseComparisonHandler(QueryHandler):
    """
    Handler for course comparison queries.
    
    These are queries that ask about similarities or differences between
    the requirements of multiple UC courses, such as:
    - "Does BILD 2 require the same BIOL series as BILD 1?"
    - "Are the prerequisites for CSE 8A different from CSE 11?"
    - "Do both MATH 20A and MATH 18 accept the same De Anza courses?"
    """
    
    # Set precedence between CourseLookupHandler and PathCompletionHandler
    PRECEDENCE = 86
    
    def __init__(self, document_repository: DocumentRepository, config: Dict[str, Any]):
        """
        Initialize the course comparison handler.
        
        Args:
            document_repository: Repository for accessing articulation documents
            config: Configuration options for the handler
        """
        super().__init__(document_repository, config)
        self.matching_service = MatchingService()
        self.articulation_facade = ArticulationFacade()
    
    def can_handle(self, query: Query) -> bool:
        """
        Determine if this handler can process the query.
        
        This handler can process queries that:
        1. Have been explicitly marked as course comparison queries, or
        2. Mention at least two UC courses and contain comparison keywords
        
        Args:
            query: The query to check
            
        Returns:
            True if this handler can process the query, False otherwise
        """
        # If already classified as a comparison query
        if query.query_type == QueryType.COURSE_COMPARISON:
            return True
            
        # Otherwise check for UC courses and comparison keywords
        if len(query.uc_courses) < 2:
            return False
            
        query_lower = query.text.lower()
        comparison_keywords = [
            'same', 'similar', 'different', 'alike', 'equivalent',
            'compare', 'versus', 'vs', 'like', 'match',
            'both require', 'both need', 'both accept'
        ]
        
        return any(keyword in query_lower for keyword in comparison_keywords)
    
    def handle(self, query: Query) -> Optional[QueryResult]:
        """
        Process a course comparison query and return results.
        
        This handler extracts the UC courses being compared, retrieves their
        articulation requirements, compares them, and generates a response
        highlighting similarities and differences.
        
        Args:
            query: The query to process
            
        Returns:
            QueryResult containing the comparison analysis
        """
        uc_courses = query.uc_courses
        
        if len(uc_courses) < 2:
            logger.warning("Course comparison query with fewer than 2 UC courses")
            return QueryResult(
                raw_response="Comparison requires at least two UC courses.",
                formatted_response=(
                    "# ⚠️ I need at least two UC courses to compare\n\n"
                    "Please specify which UC courses you want to compare. For example:\n"
                    "- Does BILD 2 require the same BIOL series as BILD 1?\n"
                    "- Are the prerequisites for CSE 8A different from CSE 11?"
                )
            )
        
        # Determine if we're looking for similarities or differences based on the query
        query_lower = query.text.lower()
        looking_for_similarities = self._is_looking_for_similarities(query_lower)
        
        # Get documents for all UC courses
        course_docs = {}
        for uc_course in uc_courses:
            docs = self.document_repository.find_by_uc_course(uc_course)
            if docs:
                course_docs[uc_course] = docs
        
        # Extract articulation requirements for each course
        course_requirements = {}
        for course, docs in course_docs.items():
            if docs:
                # Take the first document that matches the course
                doc = docs[0]
                logic_block = doc.metadata.get("logic_block", {})
                
                # Get articulation options
                articulation_options = self.articulation_facade.get_articulation_options(logic_block)
                
                # Add to requirements dict
                course_requirements[course] = {
                    "logic_block": logic_block,
                    "articulation_options": articulation_options,
                    "title": doc.metadata.get("uc_title", ""),
                    "no_articulation": logic_block.get("no_articulation", False)
                }
        
        # Compare requirements and generate response
        return self._compare_requirements(
            uc_courses, 
            course_requirements, 
            looking_for_similarities,
            query_lower
        )
    
    def _is_looking_for_similarities(self, query_text: str) -> bool:
        """
        Determine if the query is asking about similarities or differences.
        
        Args:
            query_text: The lowercase query text
            
        Returns:
            True if looking for similarities, False if looking for differences
        """
        # Keywords indicating interest in similarities
        similarity_keywords = ['same', 'similar', 'alike', 'equivalent', 'both']
        
        # Keywords indicating interest in differences
        difference_keywords = ['different', 'difference', 'unlike', 'vary', 'distinct']
        
        # Count matches for each category
        similarity_count = sum(1 for kw in similarity_keywords if kw in query_text)
        difference_count = sum(1 for kw in difference_keywords if kw in query_text)
        
        # Default to similarities if unclear
        return similarity_count >= difference_count
    
    def _extract_series_from_query(self, query_text: str) -> Optional[str]:
        """
        Extract the specific course series being compared, if mentioned.
        
        Args:
            query_text: The query text
            
        Returns:
            The course series prefix (e.g., "BIOL", "MATH") or None if not found
        """
        # Patterns for extracting series
        series_patterns = [
            r'same\s+(\w+)\s+series',
            r'same\s+(\w+)\s+courses',
            r'same\s+(\w+)\s+requirements',
            r'different\s+(\w+)\s+series',
            r'different\s+(\w+)\s+courses'
        ]
        
        for pattern in series_patterns:
            match = re.search(pattern, query_text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
                
        return None
    
    def _compare_requirements(
        self,
        uc_courses: List[str],
        course_requirements: Dict[str, Dict[str, Any]],
        looking_for_similarities: bool,
        query_text: str
    ) -> QueryResult:
        """
        Compare requirements between UC courses and generate a response.
        
        Args:
            uc_courses: List of UC courses to compare
            course_requirements: Dictionary of course requirements
            looking_for_similarities: Whether to focus on similarities or differences
            query_text: The original query text
            
        Returns:
            QueryResult with the comparison analysis
        """
        # Check if we have requirements for all courses
        missing_courses = [course for course in uc_courses if course not in course_requirements]
        if missing_courses:
            missing_list = ", ".join(missing_courses)
            return QueryResult(
                raw_response=f"No articulation data found for: {missing_list}",
                formatted_response=(
                    f"# ⚠️ Missing articulation data\n\n"
                    f"I don't have articulation information for: {missing_list}\n\n"
                    f"Please try with other UC courses or check if the course codes are correct."
                )
            )
        
        # Extract the specific series being asked about, if any
        target_series = self._extract_series_from_query(query_text)
        
        # Compare no_articulation status
        no_articulation_courses = [
            course for course, data in course_requirements.items()
            if data.get("no_articulation", False)
        ]
        
        if no_articulation_courses:
            if len(no_articulation_courses) == len(uc_courses):
                # All courses have no articulation
                return QueryResult(
                    raw_response=f"None of these courses have articulation options.",
                    formatted_response=(
                        f"# ℹ️ No articulation for any of these courses\n\n"
                        f"None of the courses you asked about ({', '.join(uc_courses)}) "
                        f"have articulation options from De Anza College."
                    )
                )
            else:
                # Some courses have no articulation
                no_art_list = ", ".join(no_articulation_courses)
                has_art = [c for c in uc_courses if c not in no_articulation_courses]
                has_art_list = ", ".join(has_art)
                
                return QueryResult(
                    raw_response=(
                        f"The following courses have no articulation: {no_art_list}. "
                        f"The following courses do have articulation options: {has_art_list}."
                    ),
                    formatted_response=(
                        f"# ⚠️ Some courses have no articulation\n\n"
                        f"The following courses have no articulation from De Anza College: {no_art_list}\n\n"
                        f"The following courses do have articulation options: {has_art_list}\n\n"
                        f"This means I cannot fully compare their requirements."
                    )
                )
        
        # Extract course options for each course
        course_options = {}
        for course, data in course_requirements.items():
            options = self._extract_course_codes_from_options(data.get("articulation_options", {}))
            course_options[course] = options
        
        # Filter by target series if specified
        if target_series:
            filtered_options = {}
            for course, options in course_options.items():
                filtered = []
                for option in options:
                    courses = option.get("courses", [])
                    series_courses = [c for c in courses if c.startswith(target_series)]
                    if series_courses:
                        filtered.append({
                            "courses": series_courses,
                            "is_and": option.get("is_and", False)
                        })
                filtered_options[course] = filtered
            course_options = filtered_options
        
        # Compare the course options
        if len(uc_courses) == 2:
            # Simple comparison between two courses
            return self._compare_two_courses(
                uc_courses[0],
                uc_courses[1],
                course_options[uc_courses[0]],
                course_options[uc_courses[1]],
                course_requirements[uc_courses[0]].get("title", ""),
                course_requirements[uc_courses[1]].get("title", ""),
                looking_for_similarities,
                target_series
            )
        else:
            # Multi-course comparison
            return self._compare_multiple_courses(
                uc_courses,
                course_options,
                course_requirements,
                looking_for_similarities,
                target_series
            )
    
    def _extract_course_codes_from_options(self, articulation_options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract course codes from articulation options structure.
        
        Handles the complex nested structure returned by articulation_facade.get_articulation_options
        
        Args:
            articulation_options: The options structure returned by the articulation facade
            
        Returns:
            List of simplified option objects with course codes and AND/OR relationship
        """
        result = []
        options = articulation_options.get("options", [])
        
        # Debug logging
        logger.debug(f"Extracting course codes from: {articulation_options}")
        
        for option in options:
            courses_data = option.get("courses", [])
            logger.debug(f"Processing option with courses: {courses_data}")
            
            # Handle each course item
            for course_item in courses_data:
                logger.debug(f"Processing course item: {course_item}")
                
                if isinstance(course_item, dict):
                    # Handle AND groups
                    if course_item.get("type") == "AND":
                        and_courses = []
                        for course in course_item.get("courses", []):
                            if isinstance(course, dict) and "name" in course:
                                and_courses.append(course.get("name"))
                            elif isinstance(course, str):
                                and_courses.append(course)
                        
                        logger.debug(f"Found AND group with courses: {and_courses}")
                        if and_courses:
                            result.append({
                                "courses": and_courses,
                                "is_and": True
                            })
                    # Handle single courses
                    elif "name" in course_item:
                        course_name = course_item.get("name", "")
                        if course_name:
                            logger.debug(f"Found single course: {course_name}")
                            result.append({
                                "courses": [course_name],
                                "is_and": False
                            })
                # Handle direct string courses
                elif isinstance(course_item, str):
                    logger.debug(f"Found direct string course: {course_item}")
                    result.append({
                        "courses": [course_item],
                        "is_and": False
                    })
        
        logger.debug(f"Extracted course options: {result}")
        return result
    
    def _compare_two_courses(
        self,
        course1: str,
        course2: str,
        options1: List[Dict[str, Any]],
        options2: List[Dict[str, Any]],
        title1: str,
        title2: str,
        looking_for_similarities: bool,
        target_series: Optional[str]
    ) -> QueryResult:
        """
        Compare requirements between two UC courses and generate a detailed response.
        
        Args:
            course1: First UC course
            course2: Second UC course
            options1: Articulation options for first course
            options2: Articulation options for second course
            title1: Title of first course
            title2: Title of second course
            looking_for_similarities: Whether to focus on similarities or differences
            target_series: Specific course series to focus on, if any
            
        Returns:
            QueryResult with the comparison analysis
        """
        # Extract course lists from options
        courses1 = set()
        for option in options1:
            if option.get("is_and", False):
                # For AND blocks, add as a tuple to preserve the combination
                courses1.add(tuple(sorted(option.get("courses", []))))
            else:
                # For OR blocks, add individual courses
                for course in option.get("courses", []):
                    courses1.add(course)
        
        courses2 = set()
        for option in options2:
            if option.get("is_and", False):
                # For AND blocks, add as a tuple to preserve the combination
                courses2.add(tuple(sorted(option.get("courses", []))))
            else:
                # For OR blocks, add individual courses
                for course in option.get("courses", []):
                    courses2.add(course)
        
        # Find common and unique courses
        common_courses = set()
        common_combos = set()
        
        for item in courses1:
            if isinstance(item, tuple):
                if item in courses2:
                    common_combos.add(item)
            elif item in courses2:
                common_courses.add(item)
        
        unique_to_1 = set()
        for item in courses1:
            if isinstance(item, tuple):
                if item not in courses2:
                    unique_to_1.add(item)
            elif item not in courses2:
                unique_to_1.add(item)
        
        unique_to_2 = set()
        for item in courses2:
            if isinstance(item, tuple):
                if item not in courses1:
                    unique_to_2.add(item)
            elif item not in courses1:
                unique_to_2.add(item)
        
        # Format course combinations for display
        format_combo = lambda combo: " + ".join(combo) if isinstance(combo, tuple) else combo
        
        # Generate response based on similarities or differences
        if looking_for_similarities:
            # User is asking about similarities
            if common_courses or common_combos:
                formatted_common = [format_combo(c) for c in common_courses.union(common_combos)]
                response = (
                    f"# ✅ Yes, {course1} and {course2} accept some of the same courses\n\n"
                    f"**{course1}** ({title1}) and **{course2}** ({title2}) "
                )
                
                if target_series:
                    response += f"both accept {target_series} courses from De Anza College.\n\n"
                else:
                    response += f"have overlapping requirements and accept some of the same courses from De Anza College.\n\n"
                
                response += f"**Courses accepted by both:** {', '.join(sorted(formatted_common))}"
                
                if unique_to_1 or unique_to_2:
                    response += "\n\n**However, there are some differences:**\n\n"
                    
                    if unique_to_1:
                        formatted_unique = [format_combo(c) for c in unique_to_1]
                        response += f"- Courses only accepted by {course1}: {', '.join(sorted(formatted_unique))}\n"
                    
                    if unique_to_2:
                        formatted_unique = [format_combo(c) for c in unique_to_2]
                        response += f"- Courses only accepted by {course2}: {', '.join(sorted(formatted_unique))}"
            else:
                # No common courses
                response = (
                    f"# ❌ No, {course1} and {course2} don't accept the same courses\n\n"
                    f"**{course1}** ({title1}) and **{course2}** ({title2}) accept different sets of De Anza courses "
                )
                
                if target_series:
                    response += f"from the {target_series} series.\n\n"
                else:
                    response += "with no overlap.\n\n"
                
                # Always show what courses each accepts for clarity
                formatted_courses1 = [format_combo(c) for c in courses1]
                formatted_courses1_str = ', '.join(sorted(formatted_courses1)) if formatted_courses1 else "None"
                response += f"**Courses accepted by {course1}:** {formatted_courses1_str}\n\n"
                
                formatted_courses2 = [format_combo(c) for c in courses2]
                formatted_courses2_str = ', '.join(sorted(formatted_courses2)) if formatted_courses2 else "None"
                response += f"**Courses accepted by {course2}:** {formatted_courses2_str}"
        else:
            # User is asking about differences
            if unique_to_1 or unique_to_2:
                response = (
                    f"# ✅ Yes, {course1} and {course2} have different requirements\n\n"
                    f"**{course1}** ({title1}) and **{course2}** ({title2}) "
                )
                
                if target_series:
                    response += f"have different requirements for {target_series} courses from De Anza College.\n\n"
                else:
                    response += f"accept different courses from De Anza College.\n\n"
                
                # Always include the specific courses for clarity
                formatted_courses1 = [format_combo(c) for c in courses1]
                formatted_courses1_str = ', '.join(sorted(formatted_courses1)) if formatted_courses1 else "None"
                response += f"**Courses accepted by {course1}:** {formatted_courses1_str}\n\n"
                
                formatted_courses2 = [format_combo(c) for c in courses2]
                formatted_courses2_str = ', '.join(sorted(formatted_courses2)) if formatted_courses2 else "None"
                response += f"**Courses accepted by {course2}:** {formatted_courses2_str}"
                
                if common_courses or common_combos:
                    formatted_common = [format_combo(c) for c in common_courses.union(common_combos)]
                    response += f"\n\n**Courses accepted by both:** {', '.join(sorted(formatted_common))}"
            else:
                # No differences
                response = (
                    f"# ❌ No, {course1} and {course2} have identical requirements\n\n"
                    f"**{course1}** ({title1}) and **{course2}** ({title2}) "
                )
                
                if target_series:
                    response += f"have the same requirements for {target_series} courses from De Anza College.\n\n"
                else:
                    response += f"accept the exact same courses from De Anza College.\n\n"
                
                if common_courses or common_combos:
                    formatted_common = [format_combo(c) for c in common_courses.union(common_combos)]
                    formatted_common_str = ', '.join(sorted(formatted_common)) if formatted_common else "None"
                    response += f"**Courses accepted by both:** {formatted_common_str}"
        
        # Create raw response
        raw_response = f"Comparison between {course1} and {course2}. "
        
        if common_courses or common_combos:
            formatted_common = [format_combo(c) for c in common_courses.union(common_combos)]
            raw_response += f"Common courses: {', '.join(sorted(formatted_common))}. "
        
        if unique_to_1:
            formatted_unique = [format_combo(c) for c in unique_to_1]
            raw_response += f"Unique to {course1}: {', '.join(sorted(formatted_unique))}. "
        
        if unique_to_2:
            formatted_unique = [format_combo(c) for c in unique_to_2]
            raw_response += f"Unique to {course2}: {', '.join(sorted(formatted_unique))}."
        
        # Create metadata
        metadata = {
            "compared_courses": [course1, course2],
            "common_courses": list(common_courses),
            "common_combinations": [list(combo) for combo in common_combos],
            "unique_to_first": [item if not isinstance(item, tuple) else list(item) for item in unique_to_1],
            "unique_to_second": [item if not isinstance(item, tuple) else list(item) for item in unique_to_2],
            "target_series": target_series,
            "looking_for_similarities": looking_for_similarities
        }
        
        return QueryResult(
            raw_response=raw_response,
            formatted_response=response,
            metadata=metadata
        )
    
    def _compare_multiple_courses(
        self,
        courses: List[str],
        course_options: Dict[str, List[Dict[str, Any]]],
        course_requirements: Dict[str, Dict[str, Any]],
        looking_for_similarities: bool,
        target_series: Optional[str]
    ) -> QueryResult:
        """
        Compare requirements between multiple UC courses.
        
        Args:
            courses: List of UC courses to compare
            course_options: Dictionary of course articulation options
            course_requirements: Dictionary of course requirements
            looking_for_similarities: Whether to focus on similarities or differences
            target_series: Specific course series to focus on, if any
            
        Returns:
            QueryResult with the comparison analysis
        """
        # For multiple courses, list all courses and their requirements
        # Then summarize common requirements across all courses
        
        # Extract all unique accepted courses across all UC courses
        all_accepted_courses = {}
        for uc_course, options in course_options.items():
            accepted_courses = set()
            accepted_combos = set()
            
            for option in options:
                if option.get("is_and", False):
                    accepted_combos.add(tuple(sorted(option.get("courses", []))))
                else:
                    accepted_courses.update(option.get("courses", []))
            
            all_accepted_courses[uc_course] = {
                "single": accepted_courses,
                "combos": accepted_combos,
                "title": course_requirements[uc_course].get("title", "")
            }
        
        # Find courses that are accepted by all UC courses
        common_courses = set()
        if all_accepted_courses:
            # Start with courses accepted by the first UC course
            first_course = courses[0]
            common_courses = all_accepted_courses[first_course]["single"].copy()
            
            # Intersect with courses accepted by each other UC course
            for uc_course in courses[1:]:
                common_courses &= all_accepted_courses[uc_course]["single"]
        
        # Generate response
        if looking_for_similarities:
            if common_courses:
                response = (
                    f"# ✅ Yes, these courses share common requirements\n\n"
                    f"The following UC courses have overlapping requirements:\n\n"
                )
                
                for uc_course in courses:
                    title = all_accepted_courses[uc_course]["title"]
                    response += f"- **{uc_course}** ({title})\n"
                
                response += f"\n**Courses accepted by all of them:** {', '.join(sorted(common_courses))}\n\n"
                
                # Add unique requirements for each course
                response += "**Unique requirements:**\n\n"
                for uc_course in courses:
                    unique = all_accepted_courses[uc_course]["single"] - common_courses
                    if unique:
                        response += f"- **{uc_course}** also accepts: {', '.join(sorted(unique))}\n"
            else:
                response = (
                    f"# ❌ No, these courses don't share common requirements\n\n"
                    f"The following UC courses have different articulation requirements:\n\n"
                )
                
                for uc_course in courses:
                    title = all_accepted_courses[uc_course]["title"]
                    accepted = all_accepted_courses[uc_course]["single"]
                    response += f"- **{uc_course}** ({title}) accepts: {', '.join(sorted(accepted))}\n"
        else:
            # Looking for differences
            if len(set.union(*[all_accepted_courses[c]["single"] for c in courses])) > len(common_courses):
                response = (
                    f"# ✅ Yes, these courses have different requirements\n\n"
                    f"The following UC courses have different articulation requirements:\n\n"
                )
                
                for uc_course in courses:
                    title = all_accepted_courses[uc_course]["title"]
                    accepted = all_accepted_courses[uc_course]["single"]
                    response += f"- **{uc_course}** ({title}) accepts: {', '.join(sorted(accepted))}\n"
                
                if common_courses:
                    response += f"\n**However, they all accept:** {', '.join(sorted(common_courses))}"
            else:
                response = (
                    f"# ❌ No, these courses have identical requirements\n\n"
                    f"The following UC courses have the same articulation requirements:\n\n"
                )
                
                for uc_course in courses:
                    title = all_accepted_courses[uc_course]["title"]
                    response += f"- **{uc_course}** ({title})\n"
                
                response += f"\n**They all accept:** {', '.join(sorted(common_courses))}"
        
        # Create raw response and metadata
        raw_response = "Multi-course comparison. "
        
        if common_courses:
            raw_response += f"Common courses: {', '.join(sorted(common_courses))}. "
        
        raw_response += "Course-specific requirements: "
        for uc_course in courses:
            accepted = all_accepted_courses[uc_course]["single"]
            raw_response += f"{uc_course}: {', '.join(sorted(accepted))}. "
        
        metadata = {
            "compared_courses": courses,
            "common_courses": list(common_courses),
            "course_specific_requirements": {
                course: {
                    "single": list(data["single"]),
                    "combos": [list(combo) for combo in data["combos"]]
                }
                for course, data in all_accepted_courses.items()
            },
            "target_series": target_series,
            "looking_for_similarities": looking_for_similarities
        }
        
        return QueryResult(
            raw_response=raw_response,
            formatted_response=response,
            metadata=metadata
        ) 