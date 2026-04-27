"""Utility functions for creating standardized API responses"""
import json
from enum import Enum, IntEnum
from typing import Optional
#TODO: consider publishing a package so that this is standard across services

class HttpStatus(IntEnum):
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500


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
    ITEM_NOT_FOUND = "ITEM_NOT_FOUND"
    ITEM_ALREADY_EXISTS = "ITEM_ALREADY_EXISTS"
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"
    
    # Server errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    
    # Method errors
    INVALID_HTTP_METHOD = "INVALID_HTTP_METHOD"


def http_response(status_code: int, data: Optional[dict], request_id: Optional[str] = None) -> dict:
    """
    Create a standardized API response.

    Args:
        status_code: HTTP status code
        data: Response data
        request_id: Optional request ID for tracing

    Returns:
        Formatted API Gateway response dict
    """
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
    }
    if request_id:
        headers["X-Request-ID"] = request_id
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": "" if data is None else json.dumps(data)
    }


def error_response(
    status_code: int,
    message: str,
    code: ErrorCode,
    request_id: Optional[str] = None
) -> dict:
    """
    Standardized error response.
    Args:
        status_code: HTTP status code
        message: Human-readable error message
        code: ErrorCode enum value
        request_id: Optional request ID for tracing

    Returns:
        Formatted API Gateway response dict
    """
    return http_response(
        status_code,
        {"error": {"message": message, "code": code.value}},
        request_id
    )
