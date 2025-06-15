#!/usr/bin/env python3
"""
Simple query preprocessing for course search to handle typos and abbreviations.
"""

import re
from typing import List, Dict, Set


class CourseQueryPreprocessor:
    """Handles common typos and abbreviations in course search queries."""
    
    def __init__(self):
        # Common abbreviations students use
        self.abbreviations = {
            'calc': 'calculus',
            'bio': 'biology',
            'chem': 'chemistry',
            'comp sci': 'computer science',
            'cs': 'computer science',
            'psych': 'psychology',
            'math': 'mathematics',
            'eng': 'english',
            'engr': 'engineering',
            'phys': 'physics',
            'econ': 'economics',
            'poli sci': 'political science',
            'anthro': 'anthropology',
            'socio': 'sociology',
            'phil': 'philosophy',
            'hist': 'history',
            'geo': 'geography',
            'art hist': 'art history',
        }
        
        # Common typos students make
        self.typo_corrections = {
            'calculas': 'calculus',
            'calculuas': 'calculus',
            'chemisty': 'chemistry',
            'chemestry': 'chemistry',
            'programing': 'programming',
            'programmin': 'programming',
            'psycology': 'psychology',
            'psycholgy': 'psychology',
            'mathmatics': 'mathematics',
            'mathmatic': 'mathematics',
            'engish': 'english',
            'englsh': 'english',
            'buisness': 'business',
            'bussiness': 'business',
            'anthropolgy': 'anthropology',
            'anthopology': 'anthropology',
            'philosphy': 'philosophy',
            'philosofy': 'philosophy',
        }
        
        # Course level indicators
        self.level_indicators = {
            'intro': 'introduction',
            'basic': 'introduction',
            'beginner': 'introduction',
            'advanced': 'advanced',
            'intermediate': 'intermediate',
            'upper': 'advanced',
            'lower': 'introduction',
        }
        
        # Subject synonyms
        self.subject_synonyms = {
            'math': ['mathematics', 'calculus', 'algebra', 'statistics'],
            'science': ['biology', 'chemistry', 'physics'],
            'english': ['composition', 'writing', 'literature'],
            'history': ['american history', 'world history', 'us history'],
            'art': ['art history', 'visual arts', 'fine arts'],
        }
    
    def preprocess_query(self, query: str) -> str:
        """
        Preprocess a search query to handle typos, abbreviations, and synonyms.
        
        Args:
            query: Raw search query from user
            
        Returns:
            Preprocessed query with corrections applied
        """
        if not query or not query.strip():
            return query
        
        # Normalize the query
        processed_query = query.lower().strip()
        
        # Step 1: Fix common typos
        processed_query = self._fix_typos(processed_query)
        
        # Step 2: Expand abbreviations
        processed_query = self._expand_abbreviations(processed_query)
        
        # Step 3: Normalize level indicators
        processed_query = self._normalize_levels(processed_query)
        
        # Step 4: Clean up extra spaces
        processed_query = re.sub(r'\s+', ' ', processed_query).strip()
        
        return processed_query
    
    def _fix_typos(self, query: str) -> str:
        """Fix common typos in the query."""
        words = query.split()
        corrected_words = []
        
        for word in words:
            # Check if word is a known typo
            if word in self.typo_corrections:
                corrected_words.append(self.typo_corrections[word])
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def _expand_abbreviations(self, query: str) -> str:
        """Expand common abbreviations."""
        # Sort by length (longest first) to avoid partial replacements
        sorted_abbrevs = sorted(self.abbreviations.items(), key=lambda x: len(x[0]), reverse=True)
        
        for abbrev, expansion in sorted_abbrevs:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            query = re.sub(pattern, expansion, query)
        
        return query
    
    def _normalize_levels(self, query: str) -> str:
        """Normalize course level indicators."""
        words = query.split()
        normalized_words = []
        
        for word in words:
            if word in self.level_indicators:
                normalized_words.append(self.level_indicators[word])
            else:
                normalized_words.append(word)
        
        return ' '.join(normalized_words)
    
    def generate_query_variants(self, query: str) -> List[str]:
        """
        Generate multiple query variants for better search coverage.
        
        Args:
            query: Preprocessed query
            
        Returns:
            List of query variants to try
        """
        variants = [query]  # Start with original
        
        # Add subject synonyms
        for subject, synonyms in self.subject_synonyms.items():
            if subject in query:
                for synonym in synonyms:
                    variant = query.replace(subject, synonym)
                    if variant not in variants:
                        variants.append(variant)
        
        # Add variations with/without level indicators
        if any(level in query for level in ['introduction', 'intermediate', 'advanced']):
            # Create version without level indicators
            words = query.split()
            no_level_words = [w for w in words if w not in ['introduction', 'intermediate', 'advanced']]
            if len(no_level_words) > 0:
                no_level_query = ' '.join(no_level_words)
                if no_level_query not in variants:
                    variants.append(no_level_query)
        
        return variants
    
    def enhance_search_results(self, query: str, search_function, k: int = 5) -> List:
        """
        Enhanced search that tries multiple query variants.
        
        Args:
            query: Original user query
            search_function: Function to call for searching (e.g., vectorstore.similarity_search)
            k: Number of results to return
            
        Returns:
            Combined and deduplicated search results
        """
        # Preprocess the query
        processed_query = self.preprocess_query(query)
        
        # Generate variants
        variants = self.generate_query_variants(processed_query)
        
        # Search with each variant
        all_results = []
        seen_course_ids = set()
        
        for variant in variants:
            try:
                results = search_function(variant, k=k)
                
                for result in results:
                    # Deduplicate by course_id
                    course_id = result.metadata.get('course_id')
                    if course_id and course_id not in seen_course_ids:
                        seen_course_ids.add(course_id)
                        all_results.append(result)
                        
                        # Stop if we have enough results
                        if len(all_results) >= k:
                            break
                
                if len(all_results) >= k:
                    break
                    
            except Exception as e:
                # Log error but continue with other variants
                print(f"Search failed for variant '{variant}': {e}")
                continue
        
        return all_results[:k]


# Usage example functions
def demo_preprocessing():
    """Demonstrate the preprocessing capabilities."""
    preprocessor = CourseQueryPreprocessor()
    
    test_queries = [
        "calculas for engineering",
        "comp sci intro",
        "basic chemisty",
        "psych 101",
        "intro to bio",
        "advanced math",
        "engish composition",
        "calc 1"
    ]
    
    print("Query Preprocessing Demo:")
    print("=" * 50)
    
    for query in test_queries:
        processed = preprocessor.preprocess_query(query)
        variants = preprocessor.generate_query_variants(processed)
        
        print(f"Original: '{query}'")
        print(f"Processed: '{processed}'")
        print(f"Variants: {variants}")
        print("-" * 30)


if __name__ == "__main__":
    demo_preprocessing() 