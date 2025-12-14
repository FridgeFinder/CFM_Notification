import json
import os
import logging

try:
    from user_fridge_notifications_service import UserFridgeNotificationService
    from user_fridge_notifications_repository import UserFridgeNotificationRepository
    from response_utils import error_response, ErrorCode
except ModuleNotFoundError:
    from Notification.dependencies.python.user_fridge_notifications_service import UserFridgeNotificationService
    from Notification.dependencies.python.user_fridge_notifications_repository import UserFridgeNotificationRepository
    from Notification.dependencies.python.response_utils import error_response, ErrorCode

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

# Initialized only once per container
db_client = get_ddb_connection()
repository = UserFridgeNotificationRepository(db_client=db_client, table_name=table_name)
service = UserFridgeNotificationService(repository=repository)

def get_authenticated_user_id(event):
    """Extract userId (Firebase UUID) from JWT token claims."""
    return event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {}).get('sub')

def validate_input(user_id: str, authenticated_user_id: str, request_id: str, path: str):
    """Validate input parameters and return an error response if validation fails."""
    if not authenticated_user_id:
        #Should never happen, if it gets here it's a configuration error
        return error_response(
            500, "Authentication failed: No sub found in JWT",
            ErrorCode.INTERNAL_SERVER_ERROR,
            request_id=request_id,
            log_level="error",
            extra={'path': path}
        )
    
    if not user_id or not user_id.strip():
        return error_response(
            400, "Missing required path parameter: user_id",
            ErrorCode.MISSING_REQUIRED_FIELD,
            request_id=request_id,
            log_level="error",
            extra={"path": path}
        )
    
    if user_id != authenticated_user_id:
        return error_response(
            403, "Unauthorized: User can only access their own data",
            ErrorCode.FORBIDDEN,
            request_id=request_id,
            log_level="warning",
            extra={
                "path_user_id": user_id,
                "authenticated_user_id": authenticated_user_id,
                "path": path
            }
        )
    return None

def lambda_handler(event, context):
    """
    Get all notification preferences for a user.
    GET /v1/users/{user_id}/fridge-notifications
    """
    request_id = context.aws_request_id if context else "unknown"
    authenticated_user_id = get_authenticated_user_id(event)
    user_id = event.get("pathParameters", {}).get("user_id")
    path = event.get("rawPath", "unknown")
    
    logger.info(
        "Request received",
        extra={
            "request_id": request_id,
            "http_method": "GET",
            "user_id": user_id,
            "authenticated_user_id": authenticated_user_id,
            "path": path
        }
    )
    
    invalid = validate_input(user_id=user_id, authenticated_user_id=authenticated_user_id, request_id=request_id, path=path)
    if invalid:
        return invalid
    
    try:
        response = service.get_all_user_notifications(userId=user_id, request_id=request_id)
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "http_method": "GET",
                "user_id": user_id,
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
                "http_method": "GET",
                "user_id": user_id,
                "path": path,
                "error_type": type(e).__name__
            }
        )
        return error_response(500, "Internal server error", ErrorCode.INTERNAL_SERVER_ERROR, request_id=request_id)