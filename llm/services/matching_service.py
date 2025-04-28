"""
TransferAI Matching Service

This module provides document matching capabilities for the TransferAI system.
It contains algorithms for different matching strategies and document filtering
to find the most relevant articulation documents for user queries.
"""

from typing import List, Dict, Any, Set, Optional, Tuple, Callable
import re
from llama_index.core import Document
from llama_index.core import VectorStoreIndex

from llm.services.query_service import QueryService


class MatchingService:
    """
    Service for matching documents to queries using various strategies.
    
    This service centralizes all document matching logic that was previously
    scattered throughout the TransferAI engine. It provides methods for:
    - Direct course matching by UC/CCC courses
    - Group and section matching
    - Reverse matching (finding UC courses that accept a CCC course)
    - Semantic search fallback
    
    Each matching strategy is implemented as a separate method, making the
    code more modular and testable.
    """
    
    def __init__(self, index: Optional[VectorStoreIndex] = None):
        """
        Initialize the matching service.
        
        Args:
            index: Optional vector store index for semantic search
        """
        self.index = index
        self.query_service = QueryService()
        
    def match_documents(
        self,
        documents: List[Document],
        uc_courses: Optional[List[str]] = None,
        ccc_courses: Optional[List[str]] = None,
        group_id: Optional[str] = None,
        section_id: Optional[str] = None,
        query_text: Optional[str] = None,
        limit: int = 5
    ) -> List[Document]:
        """
        Match documents based on the provided filters.
        
        This is the main entry point for document matching, which will try
        different matching strategies in order of specificity:
        1. Group/Section matching
        2. UC/CCC course matching
        3. Reverse matching (CCC → UC)
        4. Semantic search (if index is available)
        
        Args:
            documents: List of documents to search
            uc_courses: Optional list of UC course codes to match
            ccc_courses: Optional list of CCC course codes to match
            group_id: Optional group ID to match
            section_id: Optional section ID to match
            query_text: Optional query text for semantic search
            limit: Maximum number of documents to return
            
        Returns:
            List of matched documents, filtered and ranked by relevance
        """
        matches = []
        
        # Step 1: Group/Section match (most specific)
        if section_id and group_id:
            section_matches = self.match_by_section(documents, group_id, section_id)
            if section_matches:
                return self._filter_and_rank(section_matches, limit)
        elif group_id:
            group_matches = self.match_by_group(documents, group_id)
            if group_matches:
                return self._filter_and_rank(group_matches, limit)
                
        # Step 2: UC/CCC course match
        if uc_courses or ccc_courses:
            course_matches = self.match_by_courses(documents, uc_courses, ccc_courses)
            if course_matches:
                matches.extend(course_matches)
                
        # Step 3: Reverse match (CCC → UC) if no matches yet and we have CCC courses
        if not matches and ccc_courses and query_text:
            reverse_matches = self.match_reverse(documents, ccc_courses, query_text)
            if reverse_matches:
                matches.extend(reverse_matches)
                
        # Step 4: Semantic search fallback
        if not matches and query_text and self.index:
            semantic_matches = self.match_semantic(query_text)
            if semantic_matches:
                matches.extend(semantic_matches)
                
        # Filter and rank the results
        return self._filter_and_rank(matches, limit)
    
    def match_by_courses(
        self, 
        documents: List[Document], 
        uc_courses: Optional[List[str]] = None,
        ccc_courses: Optional[List[str]] = None
    ) -> List[Document]:
        """
        Match documents by UC and/or CCC courses.
        
        Args:
            documents: List of documents to search
            uc_courses: Optional list of UC course codes
            ccc_courses: Optional list of CCC course codes
            
        Returns:
            List of documents that match the specified courses
        """
        if not uc_courses and not ccc_courses:
            return []
            
        uc_filter = [uc.upper() for uc in (uc_courses or [])]
        ccc_filter = [cc.upper() for cc in (ccc_courses or [])]
        
        matched = []
        for doc in documents:
            # Skip documents without UC course or logic block
            if not doc.metadata.get("uc_course") or not doc.metadata.get("logic_block"):
                continue
                
            doc_uc = doc.metadata.get("uc_course", "").strip().upper()
            doc_ccc = [c.strip().upper() for c in doc.metadata.get("ccc_courses", [])]
            
            # Apply UC course filter if provided
            if uc_filter and doc_uc not in uc_filter:
                continue
                
            # Apply CCC course filter if provided
            if ccc_filter and not any(cc in doc_ccc for cc in ccc_filter):
                continue
                
            matched.append(doc)
            
        # Special case: Force-match UC course if normal matching fails
        if not matched and uc_filter:
            force_matched = [
                doc for doc in documents
                if doc.metadata.get("uc_course", "").strip().upper() in uc_filter and
                doc.metadata.get("logic_block")
            ]
            if force_matched:
                return force_matched
                
        return matched
    
    def match_by_group(self, documents: List[Document], group_id: str) -> List[Document]:
        """
        Match documents belonging to a specific group.
        
        Args:
            documents: List of documents to search
            group_id: Group ID to match
            
        Returns:
            List of documents that belong to the specified group
        """
        return [
            doc for doc in documents
            if str(doc.metadata.get("group", "")).strip() == str(group_id).strip()
        ]
        
    def match_by_section(self, documents: List[Document], group_id: str, section_id: str) -> List[Document]:
        """
        Match documents belonging to a specific section of a group.
        
        Args:
            documents: List of documents to search
            group_id: Group ID to match
            section_id: Section ID to match
            
        Returns:
            List of documents that belong to the specified section and group
        """
        return [
            doc for doc in documents
            if str(doc.metadata.get("group", "")).strip() == str(group_id).strip() and
               str(doc.metadata.get("section", "")).strip().upper() == str(section_id).strip().upper()
        ]
        
    def match_reverse(
        self, 
        documents: List[Document], 
        ccc_courses: List[str],
        query_text: str
    ) -> List[Document]:
        """
        Find UC courses that can be satisfied by specific CCC courses.
        
        This implements a "reverse" lookup - instead of finding CCC courses that
        satisfy a UC course, it finds UC courses that can be satisfied by
        given CCC courses.
        
        Args:
            documents: List of documents to search
            ccc_courses: List of CCC course codes
            query_text: Original query text
            
        Returns:
            List of UC course documents that can be satisfied by the CCC courses
        """
        matches = []
        
        # Method 1: Direct reverse match based on query text
        reverse_text_matches = self.query_service.extract_reverse_matches(query_text, documents)
        if reverse_text_matches:
            matches.extend(reverse_text_matches)
            
        # Method 2: Find UC courses satisfied by each CCC course
        for ccc in ccc_courses:
            reverse_course_matches = self.query_service.find_uc_courses_satisfied_by(ccc, documents)
            if reverse_course_matches:
                matches.extend(reverse_course_matches)
                
        return matches
    
    def match_semantic(self, query_text: str, top_k: int = 10) -> List[Document]:
        """
        Perform semantic search on the document index.
        
        This is used as a fallback when other matching methods don't return
        relevant results.
        
        Args:
            query_text: Query text to search for
            top_k: Maximum number of results to return
            
        Returns:
            List of semantically matching documents
        """
        if not self.index:
            return []
            
        try:
            query_engine = self.index.as_query_engine(similarity_top_k=top_k)
            response = query_engine.query(query_text)
            
            if hasattr(response, "source_nodes"):
                return [node.node for node in response.source_nodes]
                
        except Exception as e:
            print(f"Semantic search error: {e}")
            
        return []
    
    def validate_same_section(self, documents: List[Document]) -> List[Document]:
        """
        Filter documents to keep only those in the same section as the first document.
        
        This is used to ensure consistency in responses about specific articulation
        requirements, which can vary across sections.
        
        Args:
            documents: List of documents to filter
            
        Returns:
            List of documents all belonging to the same section
        """
        if not documents:
            return []
            
        section = documents[0].metadata.get("section")
        if not section:
            return documents
            
        return [d for d in documents if d.metadata.get("section") == section]
    
    def filter_relevant_uc_courses(self, documents: List[Document], query_text: str) -> List[Document]:
        """
        Filter documents to keep those whose UC courses are mentioned in the query.
        
        This improves relevance when multiple potential matches are found.
        
        Args:
            documents: List of documents to filter
            query_text: Original query text
            
        Returns:
            Filtered list of documents
        """
        if not documents or len(documents) <= 1:
            return documents
            
        # Extract UC course mentions from the query
        query_uc_matches = {
            self.query_service.normalize_course_code(token)
            for token in re.findall(r"[A-Z]{2,8}\s?\d+[A-Z]{0,2}", query_text.upper())
        }
        
        if not query_uc_matches:
            return documents
            
        # Filter documents to those matching courses mentioned in the query
        filtered = [
            doc for doc in documents
            if self.query_service.normalize_course_code(doc.metadata.get("uc_course", "")) in query_uc_matches
        ]
        
        # Return the filtered list if not empty, otherwise return the original first document
        return filtered if filtered else [documents[0]]
    
    def _filter_and_rank(self, documents: List[Document], limit: int = 5) -> List[Document]:
        """
        Filter and rank documents by relevance.
        
        Args:
            documents: List of documents to filter and rank
            limit: Maximum number of documents to return
            
        Returns:
            Filtered and ranked list of documents
        """
        # Remove duplicates while preserving order
        unique_docs = []
        seen_ids = set()
        
        for doc in documents:
            doc_id = self._get_document_id(doc)
            if doc_id not in seen_ids:
                unique_docs.append(doc)
                seen_ids.add(doc_id)
                
        # Rank by priority (currently just limiting to top N)
        # This could be expanded with more sophisticated ranking in the future
        return unique_docs[:limit]
    
    def _get_document_id(self, doc: Document) -> str:
        """
        Get a unique identifier for a document based on its metadata.
        
        Args:
            doc: Document to identify
            
        Returns:
            String identifier
        """
        uc_course = doc.metadata.get("uc_course", "")
        group = doc.metadata.get("group", "")
        section = doc.metadata.get("section", "")
        
        return f"{uc_course}_{group}_{section}"
