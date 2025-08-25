from boto3.dynamodb.types import TypeSerializer
from boto3.dynamodb.types import TypeDeserializer
from datetime import datetime, timezone
from user_fridge_notifications_model import UserFridgeNotificationModel
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
        except self.db_client.exceptions.ConditionalCheckFailedException as e:
            error_message = f"UserFridgeNotification with user_id: {user_notification_model.user_id}, and fridge_id: {user_notification_model.fridge_id} already exists"
            return ApiResponse(status_code=409, body={"message": error_message})
        except ClientError as e:
            logger.error("DynamoDB error: %s", e, exc_info=True)
            return ApiResponse(status_code=500, body={"message": "Database Error"})

    def put_user_fridge_notification(self, user_notification_model: UserFridgeNotificationModel) -> ApiResponse:
        #TODO: implement
        pass


def dict_to_dynamodb(data: dict) -> dict:
     serializer = TypeSerializer()
     return {k: serializer.serialize(v) for k, v in data.items()}

def dynamodb_to_dict(ddb_item: dict) -> dict:
    deserializer = TypeDeserializer()
    return {k: deserializer.deserialize(v) for k, v in ddb_item.items()}

