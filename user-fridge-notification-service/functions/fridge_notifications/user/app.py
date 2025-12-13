from pydantic import ValidationError
import os
import logging
import json
import requests

try:
    from user_fridge_notifications_model import UserFridgeNotificationModel
    from user_fridge_notifications_service import UserFridgeNotificationService
    from user_fridge_notifications_repository import UserFridgeNotificationRepository
    from response_utils import error_response, ErrorCode
except ModuleNotFoundError:
    # Fallback: absolute imports (works when package is installed / running tests)
    from Notification.dependencies.python.user_fridge_notifications_model import UserFridgeNotificationModel
    from Notification.dependencies.python.user_fridge_notifications_service import UserFridgeNotificationService
    from Notification.dependencies.python.user_fridge_notifications_repository import UserFridgeNotificationRepository
    from Notification.dependencies.python.response_utils import error_response, ErrorCode

# Setup logger first
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_ddb_connection() -> object:
    """Create a DynamoDB client; uses LocalStack when env is 'local'."""
    import boto3
    env = os.environ["DEPLOYMENT_TARGET"]
    if env == "aws":
        return boto3.client("dynamodb")
    else:
        return boto3.client("dynamodb", endpoint_url="http://localstack:4566/")

# Get Environment variables
table_name = os.environ["TABLE_NAME"]
logger.info("TABLE_NAME=%s", table_name)

# Initialized only once per container
db_client = get_ddb_connection()
repository = UserFridgeNotificationRepository(db_client=db_client, table_name=table_name)
service = UserFridgeNotificationService(repository=repository)

def get_authenticated_user_id(event):
    """
    Extract userId (Firebase UUID) from JWT token claims
    API Gateway v2 (HTTP API) provides JWT claims in requestContext.authorizer.jwt.claims
    Args:
        event: API Gateway HTTP API event
    Returns:
        User ID from JWT 'sub' claim
    """
    # For HTTP API with JWT authorizer, user ID is in the 'sub' claim
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {}).get('sub')
    return user_id

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
    # Should never get here if API Gateway JWT authorizer is configured correctly
    if not authenticated_user_id:
        return error_response(
            500, "Authentication failed: No sub found in JWT", 
            ErrorCode.INTERNAL_SERVER_ERROR,
            request_id=request_id,
            log_level="error",
            extra={'path': path}
        )
    
    # Validate required path parameters
    if not fridge_id:
        return error_response(
            400, "Missing required path parameter: fridge_id", 
            ErrorCode.MISSING_REQUIRED_FIELD,
            request_id=request_id,
            log_level="error",
            extra={"user_id": user_id, "path": path}
        )
    
    if not user_id:
        return error_response(
            400, "Missing required path parameter: user_id", 
            ErrorCode.MISSING_REQUIRED_FIELD,
            request_id=request_id,
            log_level="error",
            extra={"fridge_id": fridge_id, "path": path}
        )
    
    # NOTE: don't need user_id in pathParameters but if we ever want to allow for ADMIN users to 
    # access other users' notifications we can keep it
    # Enforce that the authenticated user can only access their own notifications
    if user_id != authenticated_user_id:
        return error_response(
            403, "Unauthorized: User can only access their own data", 
            ErrorCode.FORBIDDEN,
            request_id=request_id,
            log_level="warning",
            extra={
                "path_user_id": user_id,
                "authenticated_user_id": authenticated_user_id,
                "http_method": http_method,
                "path": path
            }
        )
    
    return None  # All validations passed


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
        return error_response(400, "Missing request body", ErrorCode.MISSING_BODY) 
    try:
        body_dict = json.loads(body)
        body_dict["userId"] = userId
        body_dict["fridgeId"] = fridgeId
        model = UserFridgeNotificationModel(**body_dict)
        return service.post_user_fridge_notification(user_notification_model=model, request_id=request_id)
    except json.JSONDecodeError:
        return error_response(400, "Invalid JSON in request body", ErrorCode.INVALID_JSON)
    except ValidationError as ve:
        return error_response(400, str(ve), ErrorCode.VALIDATION_ERROR)


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
        return error_response(400, "Missing request body", ErrorCode.MISSING_BODY)
    
    try:
        body_dict = json.loads(body)
        # Only contactTypePreferences can be updated
        contactTypePreferences = body_dict.get("contactTypePreferences")
        if not contactTypePreferences:
            return error_response(400, "contactTypePreferences is required", ErrorCode.MISSING_REQUIRED_FIELD)
        
        return service.patch_user_fridge_notification(
            userId=userId,
            fridgeId=fridgeId,
            contactTypePreferences=contactTypePreferences,
            request_id=request_id
        )
    except json.JSONDecodeError:
        return error_response(400, "Invalid JSON in request body", ErrorCode.INVALID_JSON)
    except ValidationError as ve:
        return error_response(400, str(ve), ErrorCode.VALIDATION_ERROR)


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
    # Extract request details
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
            return error_response(
                status_code=500, 
                message="Invalid HTTP method", 
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                request_id=request_id,
                log_level="error",
                extra={
                    "http_method": http_method,
                    "path": path
                }
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
        return error_response(500, "Internal server error", ErrorCode.INTERNAL_SERVER_ERROR, request_id=request_id)
