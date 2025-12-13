"""Utility functions for creating standardized API responses"""
import json
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger()


class ErrorCode(str, Enum):
    """Enum for standardized error codes"""
    # Authentication/Authorization errors
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    
    # Validation errors
    MISSING_BODY = "MISSING_BODY"
    INVALID_JSON = "INVALID_JSON"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    IMMUTABLE_FIELD = "IMMUTABLE_FIELD"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    
    # Server errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    
    # Method errors
    INVALID_HTTP_METHOD = "INVALID_HTTP_METHOD"


class ApiResponse:
    """Standardized API response wrapper"""
    
    def __init__(self, status_code: int, body: dict, request_id: str = None):
        self.status_code = status_code
        self.body = body
        self.request_id = request_id

    def api_format(self) -> dict:
        """Format response for API Gateway"""
        headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        }
        
        # Add request ID to response headers for client-side tracing
        if self.request_id:
            headers["X-Request-ID"] = self.request_id
        
        return {
            "statusCode": self.status_code,
            "headers": headers,
            "body": json.dumps(self.body)
        }


def error_response(
    status_code: int, 
    message: str, 
    code: ErrorCode, 
    request_id: Optional[str] = None,
    log_level: Optional[str] = None,
    extra: Optional[dict] = None
) -> dict:
    """
    Create a standardized error response with optional logging.
    
    Args:
        status_code: HTTP status code
        message: Human-readable error message
        code: ErrorCode enum value
        request_id: Optional request ID for tracing
        log_level: Optional log level ('info', 'warning', 'error'). If provided, will log with structured context.
        extra: Optional dict of additional context fields for structured logging (e.g., {"user_id": "123", "operation": "get"})
        
    Returns:
        Formatted API Gateway response dict
        
    Examples:
        # Simple error without logging
        return error_response(404, "Not found", ErrorCode.NOT_FOUND)
        
        # Error with automatic logging
        return error_response(
            500, "Missing fridge_id", ErrorCode.INTERNAL_SERVER_ERROR,
            request_id=request_id, 
            log_level="error", 
            extra={"user_id": user_id, "fridge_id": fridge_id}
        )
    """
    # Optional structured logging
    if log_level:
        log_func = getattr(logger, log_level.lower(), logger.info)
        log_context = extra.copy() if extra else {}
        log_context['error_code'] = code.value
        log_context['status_code'] = status_code
        if request_id:
            log_context['request_id'] = request_id
        log_func(message, extra=log_context)
    
    return ApiResponse(
        status_code=status_code,
        body={"error": {"message": message, "code": code.value}},
        request_id=request_id
    ).api_format()


def success_response(status_code: int, data: dict, request_id: str = None) -> dict:
    """
    Create a standardized success response.
    
    Args:
        status_code: HTTP status code
        data: Response data
        request_id: Optional request ID for tracing
        
    Returns:
        Formatted API Gateway response dict
    """
    return ApiResponse(
        status_code=status_code,
        body=data,
        request_id=request_id
    ).api_format()
