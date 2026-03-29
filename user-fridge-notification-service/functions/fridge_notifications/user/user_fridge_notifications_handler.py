from pydantic import ValidationError
import os
import logging
import json

from user_fridge_notifications_model import UserFridgeNotificationModel
from user_fridge_notifications_service import UserFridgeNotificationService
from user_fridge_notifications_repository import UserFridgeNotificationRepository
from response_utils import error_response, ErrorCode, HttpStatus
from dynamodb_utils import get_ddb_connection
from auth_utils import get_authenticated_user_id, validate_user_authorization

# Setup logger first
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get Environment variables
table_name = os.environ["TABLE_NAME"]
logger.info("TABLE_NAME=%s", table_name)

# Initialized only once per container
db_client = get_ddb_connection()
repository = UserFridgeNotificationRepository(db_client=db_client, table_name=table_name)
service = UserFridgeNotificationService(repository=repository)

def validate_request_parameters(
    authenticated_user_id: str,
    user_id: str,
    fridge_id: str,
    request_id: str,
    path: str,
    http_method: str
) -> dict:
    """
    Validate required request parameters from API Gateway and enforce authorization.

    Args:
        authenticated_user_id: User ID from JWT token
        user_id: User ID from path parameters
        fridge_id: Fridge ID from path parameters
        request_id: Request ID for tracing
        path: Request path for logging
        http_method: HTTP method for logging

    Returns:
        Error response dict if validation fails, None if all validations pass
    """
    # Validate required path parameters
    if not fridge_id or not fridge_id.strip():
        logger.error("Missing required path parameter: fridge_id", extra={"request_id": request_id, "user_id": user_id, "path": path})
        return error_response(
            HttpStatus.BAD_REQUEST, "Missing required path parameter: fridge_id",
            ErrorCode.MISSING_REQUIRED_FIELD,
            request_id=request_id
        )

    if not user_id or not user_id.strip():
        logger.error("Missing required path parameter: user_id", extra={"request_id": request_id, "fridge_id": fridge_id, "path": path})
        return error_response(
            HttpStatus.BAD_REQUEST, "Missing required path parameter: user_id",
            ErrorCode.MISSING_REQUIRED_FIELD,
            request_id=request_id
        )

    # NOTE: don't need user_id in pathParameters but if we ever want to allow for ADMIN users to
    # access other users' notifications we can keep it
    return validate_user_authorization(authenticated_user_id, user_id, request_id, path, http_method)


def handle_get_request(userId: str, fridgeId: str, request_id: str) -> dict:
    """
    Handle GET request to retrieve user fridge notification preferences.
    
    Args:
        userId: The authenticated user ID
        fridgeId: The fridge ID
        request_id: The request ID for tracing
        
    Returns:
        API Gateway formatted response
    """
    return service.get_user_fridge_notification(userId=userId, fridgeId=fridgeId, request_id=request_id)


def handle_post_request(event: dict, userId: str, fridgeId: str, request_id: str) -> dict:
    """
    Handle POST request to create new user fridge notification preferences.
    
    Args:
        event: Lambda event object
        userId: The authenticated user ID
        fridgeId: The fridge ID
        request_id: The request ID for tracing
        
    Returns:
        API Gateway formatted response
    """
    body = event.get("body")
    if not body:
        return error_response(HttpStatus.BAD_REQUEST, "Missing request body", ErrorCode.MISSING_BODY) 
    try:
        body_dict = json.loads(body)
        body_dict["userId"] = userId
        body_dict["fridgeId"] = fridgeId
        model = UserFridgeNotificationModel(**body_dict)
        return service.post_user_fridge_notification(user_notification_model=model, request_id=request_id)
    except json.JSONDecodeError:
        return error_response(HttpStatus.BAD_REQUEST, "Invalid JSON in request body", ErrorCode.INVALID_JSON, request_id=request_id)
    except ValidationError as ve:
        return error_response(HttpStatus.BAD_REQUEST, str(ve), ErrorCode.VALIDATION_ERROR, request_id=request_id)


def handle_patch_request(event: dict, userId: str, fridgeId: str, request_id: str) -> dict:
    """
    Handle PATCH request to partially update user fridge notification preferences.
    Only contactTypePreferences can be updated; userId and fridgeId are immutable.
    
    Args:
        event: Lambda event object
        userId: The authenticated user ID (from path, immutable)
        fridgeId: The fridge ID (from path, immutable)
        request_id: The request ID for tracing
        
    Returns:
        API Gateway formatted response
    """
    body = event.get("body")
    if not body:
        return error_response(HttpStatus.BAD_REQUEST, "Missing request body", ErrorCode.MISSING_BODY, request_id=request_id)
    
    try:
        body_dict = json.loads(body)
        # Only contactTypePreferences can be updated
        contactTypePreferences = body_dict.get("contactTypePreferences")
        if not contactTypePreferences:
            return error_response(HttpStatus.BAD_REQUEST, "contactTypePreferences is required", ErrorCode.MISSING_REQUIRED_FIELD, request_id=request_id)
        
        return service.patch_user_fridge_notification(
            userId=userId,
            fridgeId=fridgeId,
            contactTypePreferences=contactTypePreferences,
            request_id=request_id
        )
    except json.JSONDecodeError:
        return error_response(HttpStatus.BAD_REQUEST, "Invalid JSON in request body", ErrorCode.INVALID_JSON, request_id=request_id)
    except ValidationError as ve:
        return error_response(HttpStatus.BAD_REQUEST, str(ve), ErrorCode.VALIDATION_ERROR, request_id=request_id)


def handle_delete_request(userId: str, fridgeId: str, request_id: str) -> dict:
    """
    Handle DELETE request to remove user fridge notification preferences.
    
    Args:
        userId: The authenticated user ID
        fridgeId: The fridge ID
        request_id: The request ID for tracing
        
    Returns:
        API Gateway formatted response
    """
    return service.delete_user_fridge_notification(userId=userId, fridgeId=fridgeId, request_id=request_id)


def lambda_handler(event, context):     
    """
    Main Lambda handler that routes requests to appropriate method handlers.
    Args:
        event: Lambda event object from HTTP API Gateway
        context: Lambda context object
    Returns:
        API Gateway formatted response
    """
    request_id = context.aws_request_id if context else 'unknown'
    authenticated_user_id = get_authenticated_user_id(event) 
    http_method = event.get("requestContext", {}).get("http", {}).get("method")
    fridge_id = event.get("pathParameters", {}).get("fridge_id")
    user_id = event.get("pathParameters", {}).get("user_id")
    path = event.get("rawPath", "unknown")
    # Log incoming request with structured fields for CloudWatch querying
    logger.info(
        "Request received",
        extra={
            "request_id": request_id,
            "http_method": http_method,
            "user_id": user_id,
            "fridge_id": fridge_id,
            "authenticated_user_id": authenticated_user_id,
            "path": path
        }
    )
    
    # Validate request parameters and authorization
    validation_error = validate_request_parameters(
        authenticated_user_id, user_id, fridge_id, request_id, path, http_method
    )
    if validation_error:
        return validation_error

    # Route to appropriate handler based on HTTP method
    try:
        if http_method == "GET":
            response = handle_get_request(userId=user_id, fridgeId=fridge_id, request_id=request_id)
        elif http_method == "POST":
            response = handle_post_request(event=event, userId=user_id, fridgeId=fridge_id, request_id=request_id)
        elif http_method == "PATCH":
            response = handle_patch_request(event=event, userId=user_id, fridgeId=fridge_id, request_id=request_id)
        elif http_method == "DELETE":
            response = handle_delete_request(userId=user_id, fridgeId=fridge_id, request_id=request_id)
        else:
            # Should never get here - indicates a configuration error
            logger.error("Invalid HTTP method", extra={"request_id": request_id, "http_method": http_method, "path": path})
            return error_response(
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
                message="Invalid HTTP method",
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                request_id=request_id
            )
        
        # Log successful response
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "http_method": http_method,
                "user_id": user_id,
                "fridge_id": fridge_id,
                "path": path,
                "status_code": response.get("statusCode")
            }
        )
        return response
    except Exception as e:
        logger.exception(
            "Unhandled exception in lambda_handler",
            extra={
                "request_id": request_id,
                "http_method": http_method,
                "user_id": user_id,
                "fridge_id": fridge_id,
                "path": path,
                "error_type": type(e).__name__
            }
        )
        return error_response(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error", ErrorCode.INTERNAL_SERVER_ERROR, request_id=request_id)
