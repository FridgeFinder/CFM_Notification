from boto3.dynamodb.types import TypeSerializer
from boto3.dynamodb.types import TypeDeserializer
from datetime import datetime, timezone
try:
    # Preferred: relative import when running inside SAM/local container
    from user_fridge_notifications_model import UserFridgeNotificationModel
except ModuleNotFoundError:
    # Fallback: absolute import when package is installed for tests
    from Notification.dependencies.python.user_fridge_notifications_model import UserFridgeNotificationModel
import json
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ApiResponse:

    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self.body = body

    def api_format(self) -> dict:
        return {
            "statusCode": self.status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(self.body)
        }

class UserFridgeNotificationApi:
    #TODO: add auth so that only the user is able to edit their own preferences
    def __init__(self, db_client: "botocore.client.DynamoDB"):
        self.db_client = db_client

    def get_user_fridge_notification(self, user_id: str, fridge_id: str) -> ApiResponse:   
        key = {"user_id": {"S": user_id}, "fridge_id": {"S": fridge_id}} 
        try:
            result = self.db_client.get_item(TableName=UserFridgeNotificationModel.TABLE_NAME, Key=key)
            if "Item" not in result:
                return ApiResponse(
                    status_code=404, body={"message": "Item not found"}
                )
            else:
                json_data = dynamodb_to_dict(result["Item"])
                return ApiResponse(
                    status_code=200,
                    body=json_data,
                )
        except ClientError as e:
            logger.error("DynamoDB error during GET: %s", e, exc_info=True)
            return ApiResponse(status_code=500, body={"message": "Database error"})


    def post_user_fridge_notification(self, user_notification_model: UserFridgeNotificationModel) -> ApiResponse:
        current_time = datetime.now(timezone.utc)
        user_notification_model.created_at = current_time
        user_notification_model.updated_at = current_time
        dict_format = user_notification_model.model_dump(mode="json")
        serialized_data = dict_to_dynamodb(dict_format)
        try:
            self.db_client.put_item(
                TableName=UserFridgeNotificationModel.TABLE_NAME,
                Item=serialized_data,
                ConditionExpression="attribute_not_exists(user_id) AND attribute_not_exists(fridge_id)"
            )
            return ApiResponse(status_code=201, body=dict_format)
        except ClientError as e:
            error_code = e.response['Error'].get('Code')
            if error_code == "ConditionalCheckFailedException":
                error_message = f"UserFridgeNotification with user_id: {user_notification_model.user_id}, and fridge_id: {user_notification_model.fridge_id} already exists"
                return ApiResponse(status_code=409, body={"message": error_message})
            logger.error("DynamoDB error during POST: %s", e, exc_info=True)
            return ApiResponse(status_code=500, body={"message": "Database Error"})

    def put_user_fridge_notification(self, user_notification_model: UserFridgeNotificationModel) -> ApiResponse:
        """Update existing user fridge notification preferences"""
        key = {
            "user_id": {"S": user_notification_model.user_id},
            "fridge_id": {"S": user_notification_model.fridge_id}
        } 
        try:
            result = self.db_client.get_item(TableName=UserFridgeNotificationModel.TABLE_NAME, Key=key)
            if "Item" not in result:
                return ApiResponse(
                    status_code=404,
                    body={"message": "User Fridge Notification not found"}
                )
            
            #update timestamp
            current_time = datetime.now(timezone.utc)
            user_notification_model.updated_at = current_time

            #keep original created_at. Unless not set, which should not be the case
            existing_item = dynamodb_to_dict(result["Item"])
            created_at_str = existing_item.get("created_at")
            if created_at_str and isinstance(created_at_str, str):
                #created_at is of type str, but model expects type datetime. So need to convert from string -> datetime
                user_notification_model.created_at = datetime.fromisoformat(created_at_str)
            else:
                user_notification_model.created_at = current_time

            #serialize and update
            dict_format = user_notification_model.model_dump(mode="json")

            serialized_data = dict_to_dynamodb(dict_format)

            self.db_client.put_item(
                TableName=UserFridgeNotificationModel.TABLE_NAME,
                Item=serialized_data
            )

            return ApiResponse(status_code=200, body=dict_format)
        except ClientError as e:
            logger.error("DynamoDB error during PUT: %s", e, exc_info=True)
            return ApiResponse(status_code=500, body={"message": "Database Error"})


def dict_to_dynamodb(data: dict) -> dict:
     serializer = TypeSerializer()
     return {k: serializer.serialize(v) for k, v in data.items()}

def dynamodb_to_dict(ddb_item: dict) -> dict:
    deserializer = TypeDeserializer()
    return {k: deserializer.deserialize(v) for k, v in ddb_item.items()}

