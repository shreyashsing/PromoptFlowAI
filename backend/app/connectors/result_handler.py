"""
Connector result handling and error management utilities.
"""
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

from app.models.connector import ConnectorResult, ConnectorExecutionContext
from app.core.exceptions import ConnectorException


logger = logging.getLogger(__name__)


class ResultType(str, Enum):
    """Types of connector results."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


class ResultSeverity(str, Enum):
    """Severity levels for results."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConnectorResultHandler:
    """
    Handler for processing and managing connector execution results.
    
    Provides utilities for result validation, transformation, error handling,
    and result aggregation across multiple connector executions.
    """
    
    def __init__(self):
        self.execution_history: List[Dict[str, Any]] = []
    
    def create_success_result(
        self, 
        data: Any, 
        metadata: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ) -> ConnectorResult:
        """
        Create a successful connector result.
        
        Args:
            data: Result data from connector execution
            metadata: Additional metadata about the execution
            message: Optional success message
            
        Returns:
            ConnectorResult indicating success
        """
        return ConnectorResult(
            success=True,
            data=data,
            error=None,
            metadata={
                **(metadata or {}),
                "result_type": ResultType.SUCCESS,
                "timestamp": datetime.utcnow().isoformat(),
                "message": message
            }
        )
    
    def create_error_result(
        self, 
        error: Union[str, Exception], 
        data: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        severity: ResultSeverity = ResultSeverity.HIGH
    ) -> ConnectorResult:
        """
        Create an error connector result.
        
        Args:
            error: Error message or exception
            data: Partial data if available
            metadata: Additional metadata about the error
            severity: Severity level of the error
            
        Returns:
            ConnectorResult indicating error
        """
        error_message = str(error)
        if isinstance(error, Exception):
            error_message = f"{error.__class__.__name__}: {str(error)}"
        
        return ConnectorResult(
            success=False,
            data=data,
            error=error_message,
            metadata={
                **(metadata or {}),
                "result_type": ResultType.ERROR,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": error.__class__.__name__ if isinstance(error, Exception) else "GeneralError"
            }
        )
    
    def create_warning_result(
        self, 
        data: Any, 
        warning: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConnectorResult:
        """
        Create a warning connector result (success with warnings).
        
        Args:
            data: Result data from connector execution
            warning: Warning message
            metadata: Additional metadata
            
        Returns:
            ConnectorResult indicating success with warnings
        """
        return ConnectorResult(
            success=True,
            data=data,
            error=None,
            metadata={
                **(metadata or {}),
                "result_type": ResultType.WARNING,
                "warning": warning,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def create_partial_result(
        self, 
        data: Any, 
        error: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConnectorResult:
        """
        Create a partial result (some data retrieved despite errors).
        
        Args:
            data: Partial data that was successfully retrieved
            error: Error message explaining what failed
            metadata: Additional metadata
            
        Returns:
            ConnectorResult indicating partial success
        """
        return ConnectorResult(
            success=False,  # Marked as failed due to incomplete execution
            data=data,
            error=error,
            metadata={
                **(metadata or {}),
                "result_type": ResultType.PARTIAL,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def validate_result(self, result: ConnectorResult) -> bool:
        """
        Validate a connector result structure.
        
        Args:
            result: ConnectorResult to validate
            
        Returns:
            True if result is valid
            
        Raises:
            ConnectorException: If result is invalid
        """
        if not isinstance(result, ConnectorResult):
            raise ConnectorException("Result must be a ConnectorResult instance")
        
        if result.success and result.error:
            raise ConnectorException("Successful result cannot have an error message")
        
        if not result.success and not result.error:
            raise ConnectorException("Failed result must have an error message")
        
        return True
    
    def transform_result_data(
        self, 
        result: ConnectorResult, 
        transformer: callable
    ) -> ConnectorResult:
        """
        Transform result data using a provided function.
        
        Args:
            result: Original connector result
            transformer: Function to transform the data
            
        Returns:
            New ConnectorResult with transformed data
        """
        try:
            if result.data is not None:
                transformed_data = transformer(result.data)
                return ConnectorResult(
                    success=result.success,
                    data=transformed_data,
                    error=result.error,
                    metadata={
                        **result.metadata,
                        "transformed": True,
                        "transformation_timestamp": datetime.utcnow().isoformat()
                    }
                )
            return result
        except Exception as e:
            return self.create_error_result(
                f"Data transformation failed: {str(e)}",
                data=result.data,
                metadata=result.metadata
            )
    
    def merge_results(self, results: List[ConnectorResult]) -> ConnectorResult:
        """
        Merge multiple connector results into a single result.
        
        Args:
            results: List of ConnectorResult objects to merge
            
        Returns:
            Merged ConnectorResult
        """
        if not results:
            return self.create_error_result("No results to merge")
        
        if len(results) == 1:
            return results[0]
        
        # Determine overall success
        all_successful = all(r.success for r in results)
        any_successful = any(r.success for r in results)
        
        # Collect all data
        merged_data = []
        errors = []
        merged_metadata = {
            "merged_results_count": len(results),
            "merge_timestamp": datetime.utcnow().isoformat()
        }
        
        for i, result in enumerate(results):
            if result.data is not None:
                merged_data.append({
                    "index": i,
                    "success": result.success,
                    "data": result.data
                })
            
            if result.error:
                errors.append(f"Result {i}: {result.error}")
            
            # Merge metadata
            for key, value in result.metadata.items():
                if key not in merged_metadata:
                    merged_metadata[key] = []
                if not isinstance(merged_metadata[key], list):
                    merged_metadata[key] = [merged_metadata[key]]
                merged_metadata[key].append(value)
        
        # Determine result type
        if all_successful:
            return self.create_success_result(
                data=merged_data,
                metadata=merged_metadata,
                message=f"Successfully merged {len(results)} results"
            )
        elif any_successful:
            return self.create_partial_result(
                data=merged_data,
                error="; ".join(errors),
                metadata=merged_metadata
            )
        else:
            return self.create_error_result(
                error="; ".join(errors),
                data=merged_data,
                metadata=merged_metadata
            )
    
    def log_execution(
        self, 
        connector_name: str, 
        context: ConnectorExecutionContext,
        result: ConnectorResult,
        execution_time: float
    ) -> None:
        """
        Log connector execution for monitoring and debugging.
        
        Args:
            connector_name: Name of the executed connector
            context: Execution context
            result: Execution result
            execution_time: Time taken for execution in seconds
        """
        log_entry = {
            "connector_name": connector_name,
            "user_id": context.user_id,
            "workflow_id": context.workflow_id,
            "node_id": context.node_id,
            "success": result.success,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat(),
            "error": result.error,
            "data_size": len(str(result.data)) if result.data else 0,
            "metadata": result.metadata
        }
        
        self.execution_history.append(log_entry)
        
        # Log to application logger
        if result.success:
            logger.info(f"Connector {connector_name} executed successfully in {execution_time:.2f}s")
        else:
            logger.error(f"Connector {connector_name} failed: {result.error}")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics from logged executions.
        
        Returns:
            Dictionary with execution statistics
        """
        if not self.execution_history:
            return {"total_executions": 0}
        
        total = len(self.execution_history)
        successful = sum(1 for entry in self.execution_history if entry["success"])
        failed = total - successful
        
        execution_times = [entry["execution_time"] for entry in self.execution_history]
        avg_execution_time = sum(execution_times) / len(execution_times)
        
        connector_stats = {}
        for entry in self.execution_history:
            name = entry["connector_name"]
            if name not in connector_stats:
                connector_stats[name] = {"total": 0, "successful": 0, "failed": 0}
            connector_stats[name]["total"] += 1
            if entry["success"]:
                connector_stats[name]["successful"] += 1
            else:
                connector_stats[name]["failed"] += 1
        
        return {
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": successful / total if total > 0 else 0,
            "average_execution_time": avg_execution_time,
            "connector_stats": connector_stats
        }
    
    def clear_history(self) -> None:
        """Clear execution history."""
        self.execution_history.clear()


# Global result handler instance
result_handler = ConnectorResultHandler()