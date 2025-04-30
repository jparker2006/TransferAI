"""
TransferAI Handlers Module

This module contains specialized handlers for different query types.
"""

from llm.handlers.base import QueryHandler, HandlerRegistry
from llm.handlers.fallback_handler import FallbackQueryHandler
from llm.handlers.validation_handler import ValidationQueryHandler
from llm.handlers.course_handler import CourseEquivalencyHandler
from llm.handlers.course_lookup_handler import CourseLookupHandler
from llm.handlers.group_handler import GroupQueryHandler
from llm.handlers.path_completion_handler import PathCompletionHandler
from llm.handlers.honors_handler import HonorsQueryHandler
from llm.handlers.course_comparison_handler import CourseComparisonHandler

__all__ = [
    'QueryHandler',
    'HandlerRegistry',
    'FallbackQueryHandler',
    'ValidationQueryHandler',
    'CourseEquivalencyHandler',
    'CourseLookupHandler',
    'GroupQueryHandler',
    'HonorsQueryHandler',
    'PathCompletionHandler',
    'CourseComparisonHandler'
]
