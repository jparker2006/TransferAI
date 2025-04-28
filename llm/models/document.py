"""
TransferAI Document Model

This module defines the Document model used throughout the TransferAI system. It wraps 
the llama_index Document class to provide a consistent interface while adding additional
functionality specific to articulation document processing.
"""

from typing import Dict, Any, List, Optional, Union
from llama_index.core import Document as LlamaDocument


class Document:
    """
    A document representing articulation information between courses.
    
    This class wraps the llama_index Document class to provide a standardized interface
    for working with articulation documents. It adds methods specific to the TransferAI
    system while maintaining compatibility with the underlying document storage.
    
    Attributes:
        _document: The underlying llama_index Document
    """

    def __init__(
        self, 
        text: str = "", 
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        llama_document: Optional[LlamaDocument] = None
    ):
        """
        Initialize a Document instance.
        
        Args:
            text: The document text content
            metadata: Dictionary of metadata associated with the document
            doc_id: Unique identifier for the document
            embedding: Vector embedding of the document content
            llama_document: An existing llama_index Document to wrap
        """
        if llama_document:
            self._document = llama_document
        else:
            self._document = LlamaDocument(
                text=text,
                metadata=metadata or {},
                doc_id=doc_id,
                embedding=embedding
            )

    @property
    def text(self) -> str:
        """Get the document text content."""
        return self._document.text

    @text.setter
    def text(self, value: str) -> None:
        """Set the document text content."""
        self._document.text = value

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get the document metadata."""
        return self._document.metadata

    @metadata.setter
    def metadata(self, value: Dict[str, Any]) -> None:
        """Set the document metadata."""
        self._document.metadata = value

    @property
    def doc_id(self) -> Optional[str]:
        """Get the document ID."""
        return self._document.doc_id

    @doc_id.setter
    def doc_id(self, value: str) -> None:
        """Set the document ID."""
        self._document.doc_id = value

    @property
    def embedding(self) -> Optional[List[float]]:
        """Get the document embedding."""
        return self._document.embedding

    @embedding.setter
    def embedding(self, value: List[float]) -> None:
        """Set the document embedding."""
        self._document.embedding = value

    def get_uc_course(self) -> str:
        """
        Get the UC course code associated with this document.
        
        Returns:
            The UC course code as a string, or empty string if not found
        """
        return self.metadata.get("uc_course", "")

    def get_ccc_courses(self) -> List[str]:
        """
        Get the CCC courses associated with this document.
        
        Returns:
            List of CCC course codes
        """
        return self.metadata.get("ccc_courses", [])

    def get_logic_block(self) -> Dict[str, Any]:
        """
        Get the articulation logic block for this document.
        
        Returns:
            Dictionary representing the articulation logic
        """
        return self.metadata.get("logic_block", {})

    def has_honors_requirement(self) -> bool:
        """
        Check if this document has any honors course requirements.
        
        Returns:
            True if any course in the logic block requires honors, False otherwise
        """
        logic_block = self.get_logic_block()
        
        # Check for no articulation
        if logic_block.get("no_articulation", False):
            return False
            
        # Helper function to recursively check for honors requirements
        def check_for_honors(block: Dict[str, Any]) -> bool:
            if "honors" in block and block["honors"]:
                return True
                
            if "type" in block:
                if block["type"] in ("AND", "OR"):
                    for course in block.get("courses", []):
                        if check_for_honors(course):
                            return True
            return False
            
        return check_for_honors(logic_block)

    def has_no_articulation(self) -> bool:
        """
        Check if this document has no articulation path.
        
        Returns:
            True if document explicitly indicates no articulation, False otherwise
        """
        logic_block = self.get_logic_block()
        return logic_block.get("no_articulation", False)

    @classmethod
    def from_llama_document(cls, document: LlamaDocument) -> "Document":
        """
        Create a Document instance from a llama_index Document.
        
        Args:
            document: The llama_index Document to wrap
            
        Returns:
            A new Document instance wrapping the provided document
        """
        return cls(llama_document=document)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """
        Create a Document instance from a dictionary.
        
        Args:
            data: Dictionary containing document data
            
        Returns:
            A new Document instance with the provided data
        """
        return cls(
            text=data.get("text", ""),
            metadata=data.get("metadata", {}),
            doc_id=data.get("doc_id"),
            embedding=data.get("embedding")
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the document to a dictionary.
        
        Returns:
            Dictionary representation of the document
        """
        return {
            "text": self.text,
            "metadata": self.metadata,
            "doc_id": self.doc_id,
            "embedding": self.embedding
        }

    def to_llama_document(self) -> LlamaDocument:
        """
        Get the underlying llama_index Document.
        
        Returns:
            The wrapped llama_index Document
        """
        return self._document

    def __str__(self) -> str:
        """String representation of the document."""
        course = self.get_uc_course()
        course_str = f"UC Course: {course}" if course else "No UC course"
        return f"Document({course_str}, {len(self.text)} chars)"

    def __repr__(self) -> str:
        """Detailed string representation of the document."""
        return f"Document(id={self.doc_id}, uc_course={self.get_uc_course()}, ccc_courses={self.get_ccc_courses()})"
