import os
import logging

from dynamodb_utils import get_ddb_connection, dynamodb_to_dict
from response_utils import error_response, http_response, ErrorCode, HttpStatus
from auth_utils import get_authenticated_user_id, validate_user_authorization

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get Environment variables
table_name = os.environ["TABLE_NAME"]

# Initialized only once per container
db_client = get_ddb_connection()

def validate_input(user_id: str, authenticated_user_id: str, request_id: str, path: str):
    """Validate input parameters and return an error response if validation fails."""
    if not user_id or not user_id.strip():
        logger.error("Missing required path parameter: user_id", extra={"request_id": request_id, "path": path})
        return error_response(
            HttpStatus.BAD_REQUEST, "Missing required path parameter: user_id",
            ErrorCode.MISSING_REQUIRED_FIELD,
            request_id=request_id
        )
    return validate_user_authorization(authenticated_user_id, user_id, request_id, path)

def list_by_user(user_id: str) -> list:
    """
    Query DynamoDB for all notification preferences belonging to a user.

    Args:
        user_id: The user ID

    Returns:
        List of deserialized notification dicts

    Raises:
        ClientError: If DynamoDB operation fails
    """
    response = db_client.query(
        TableName=table_name,
        KeyConditionExpression="userId = :userId",
        ExpressionAttributeValues={":userId": {"S": user_id}}
    )
    return [dynamodb_to_dict(item) for item in response.get("Items", [])]


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
        notifications = list_by_user(user_id)
        result = http_response(
            HttpStatus.OK,
            {"notifications": notifications, "count": len(notifications)},
            request_id=request_id
        )
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "http_method": "GET",
                "user_id": user_id,
                "path": path,
                "status_code": result.get("statusCode")
            }
        )
        return result
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
        return error_response(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error", ErrorCode.INTERNAL_SERVER_ERROR, request_id=request_id)