import os
import logging
import json

# try:
from user_fridge_notifications_model import get_ddb_connection, UserFridgeNotificationModel
from user_fridge_notifications_api import ApiResponse, UserFridgeNotificationApi
from pydantic import ValidationError
# except ModuleNotFoundError:
#     # If it gets here it's because we are performing a unit test. It's a common error when using lambda layers
#     # Here is an example of someone having a similar issue:
#     # https://stackoverflow.com/questions/69592094/pytest-failing-in-aws-sam-project-due-to-modulenotfounderror
#     from dependencies.python.user_fridge_notifications_model import (
#         get_ddb_connection, UserFridgeNotificationModel
#     )
#     from dependencies.python.user_fridge_notifications_api import (
#         ApiResponse, UserFridgeNotificationApi
#     )
    
env = os.environ["Environment"]
#initialized only once per container
db_client = get_ddb_connection(env)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context): 
    #TODO: Add auth, only admin/user is able to update their own 
    httpMethod = event.get("httpMethod", None)
    fridge_id = event.get("pathParameters", {}).get("fridge_id", None)
    user_id = event.get("pathParameters", {}).get("user_id", None)
    api = UserFridgeNotificationApi(db_client=db_client)
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