import os
import logging
import json

try:
    from user_fridge_notifications_model import get_ddb_connection, UserFridgeNotificationModel
    from user_fridge_notifications_api import ApiResponse, UserFridgeNotificationApi
except ModuleNotFoundError:
    # Fallback: absolute imports (works when package is installed / running tests)
    from Notification.dependencies.python.user_fridge_notifications_model import get_ddb_connection, UserFridgeNotificationModel
    from Notification.dependencies.python.user_fridge_notifications_api import ApiResponse, UserFridgeNotificationApi

from pydantic import ValidationError
    
env = os.environ["Environment"]
#initialized only once per container
db_client = get_ddb_connection(env)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):     
    # Extract Cognito claims
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    
    authenticated_user_id = claims.get("sub")
    httpMethod = event.get("httpMethod", None)
    fridge_id = event.get("pathParameters", {}).get("fridge_id", None)
    user_id = event.get("pathParameters", {}).get("user_id", None)
    api = UserFridgeNotificationApi(db_client=db_client)
    #NOTE: don't need user_id in pathParameters but if we ever want to allow for ADMIN users to 
    #... access other users' notifications we can keep it
    # Enforce that the authenticated user can only access their own notifications
    if not authenticated_user_id or (user_id and user_id != authenticated_user_id):
        logger.warning(f"Unauthorized access attempt: path user_id={user_id}, auth user_id={authenticated_user_id}")
        return ApiResponse(status_code=403, body={"message": "Forbidden: You are not authorized to access this resource."}).api_format()

    ### GET API
    if httpMethod == "GET":
        api_response = api.get_user_fridge_notification(user_id=user_id, fridge_id=fridge_id)
        return api_response.api_format()

    ### POST / PUT API
    body = event.get("body", None)
    if body is None:
        return ApiResponse(400, {"message": "Missing request body"}).api_format()
    try:
        user_fridge_notification_model = build_user_fridge_notification_model(body=body, user_id=user_id, fridge_id=fridge_id)
    except ValidationError as ve:
        return ApiResponse(status_code=400, body={"message": str(ve)}).api_format()
    except ValueError as ve:
        return ApiResponse(status_code=400, body={"message": str(ve)}).api_format()
    if httpMethod == "POST":
        api_response = api.post_user_fridge_notification(user_notification_model=user_fridge_notification_model)
        return api_response.api_format()

    if httpMethod == "PUT":
        api_response = api.put_user_fridge_notification(user_notification_model=user_fridge_notification_model)
        return api_response.api_format()

    ### IF NONE OF THE ABOVE THEN THE HTTP METHOD IS INVALID
    api_response = ApiResponse(status_code=400, body={"message": "invalid http method"})
    return api_response.api_format()


def build_user_fridge_notification_model(body: str, user_id: str, fridge_id: str) -> UserFridgeNotificationModel:
    body_dict = json.loads(body)
    contact_info = body_dict.get("contact_info", None)
    contact_types_preferences = body_dict.get("contact_types_preferences", None)
    contact_types_status = body_dict.get("contact_types_status", None)
    user_fridge_notification_model = UserFridgeNotificationModel(
        user_id=user_id,
        fridge_id=fridge_id,
        contact_info=contact_info,
        contact_types_preferences=contact_types_preferences,
        contact_types_status=contact_types_status
    )
    return user_fridge_notification_model