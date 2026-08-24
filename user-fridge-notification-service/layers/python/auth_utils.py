"""Shared authentication and authorization utilities for Lambda functions."""
import logging
from typing import Optional

from response_utils import error_response, ErrorCode, HttpStatus

logger = logging.getLogger()


def get_authenticated_user_id(event: dict) -> Optional[str]:
    """
    Extract userId (Firebase UUID) from JWT token claims.
    API Gateway v2 (HTTP API) provides JWT claims in requestContext.authorizer.jwt.claims.
    """
    return event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {}).get('sub')


def validate_user_authorization(
    authenticated_user_id: str,
    user_id: str,
    request_id: str,
    path: str,
    http_method: Optional[str] = None
) -> Optional[dict]:
    """
    Validate JWT authentication and enforce user-owns-resource authorization.

    Checks that authenticated_user_id exists in the JWT claims and that
    user_id matches the authenticated user. Caller is responsible for
    validating that user_id is non-empty before calling this function.

    Args:
        authenticated_user_id: User ID extracted from JWT 'sub' claim
        user_id: User ID from path parameters (assumed non-empty)
        request_id: Request ID for tracing
        path: Request path for logging
        http_method: Optional HTTP method for logging

    Returns:
        Error response dict if validation fails, None if all validations pass
    """
    # Should never get here if API Gateway JWT authorizer is configured correctly
    if not authenticated_user_id or not authenticated_user_id.strip():
        logger.error("Authentication failed: No sub found in JWT", extra={"request_id": request_id, "path": path})
        return error_response(
            HttpStatus.INTERNAL_SERVER_ERROR, "Authentication failed: No sub found in JWT",
            ErrorCode.INTERNAL_SERVER_ERROR,
            request_id=request_id
        )

    if user_id != authenticated_user_id:
        extra = {
            "request_id": request_id,
            "path_user_id": user_id,
            "authenticated_user_id": authenticated_user_id,
            "path": path
        }
        if http_method:
            extra["http_method"] = http_method
        logger.warning("Unauthorized: User can only access their own data", extra=extra)
        return error_response(
            HttpStatus.FORBIDDEN, "Unauthorized: User can only access their own data",
            ErrorCode.FORBIDDEN,
            request_id=request_id
        )

    return None
