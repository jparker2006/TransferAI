"""TransferAI Agent Package

This package contains agent-related modules for the TransferAI system,
including DAG validation and execution utilities.
"""

from .executor import execute, ExecutorError
from .verify_dag import verify_dag, DAGValidationError

__version__ = "1.5"
__all__ = ["execute", "ExecutorError", "verify_dag", "DAGValidationError"] 