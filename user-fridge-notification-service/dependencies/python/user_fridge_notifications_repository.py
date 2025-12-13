from typing import Optional, List, Dict, Any
import logging
import os

try:
    from user_fridge_notifications_model import UserFridgeNotificationModel
except ModuleNotFoundError:
    from Notification.dependencies.python.user_fridge_notifications_model import UserFridgeNotificationModel

from boto3.dynamodb.types import TypeSerializer, TypeDeserializer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def dict_to_dynamodb(data: dict) -> dict:
    """Convert Python dict to DynamoDB format"""
    serializer = TypeSerializer()
    return {k: serializer.serialize(v) for k, v in data.items()}


def dynamodb_to_dict(ddb_item: dict) -> dict:
    """Convert DynamoDB item to Python dict"""
    deserializer = TypeDeserializer()
    return {k: deserializer.deserialize(v) for k, v in ddb_item.items()}


class UserFridgeNotificationRepository:
    """Repository for DynamoDB operations on user fridge notifications.

    Methods return plain Python dicts (deserialized from DynamoDB wire format)
    instead of Pydantic model instances.
    """
    
    def __init__(self, db_client: Any, table_name: str):
        self.db_client = db_client
        self.table_name = table_name
    
    def get(self, user_id: str, fridge_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a user fridge notification by user_id and fridge_id.
        
        Args:
            user_id: The user ID
            fridge_id: The fridge ID
            
        Returns:
            Dict[str, Any] if found, None otherwise
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        key = dict_to_dynamodb({"userId": user_id, "fridgeId": fridge_id})
        
        result = self.db_client.get_item(TableName=self.table_name, Key=key)
        
        if "Item" not in result:
            return None
        
        return dynamodb_to_dict(result["Item"])
    
    def create(self, model: UserFridgeNotificationModel) -> None:
        """
        Create a new user fridge notification.
        
        Args:
            model: The UserFridgeNotificationModel to create
            
        Raises:
            ClientError: If DynamoDB operation fails
                - ConditionalCheckFailedException if item already exists
                - Other ClientErrors for DynamoDB failures
        """
        dict_format = model.model_dump(mode="json")
        serialized_data = dict_to_dynamodb(dict_format)
        
        self.db_client.put_item(
            TableName=self.table_name,
            Item=serialized_data,
            ConditionExpression="attribute_not_exists(userId) AND attribute_not_exists(fridgeId)"
        )
    
    def update(self, ufn_model: UserFridgeNotificationModel) -> None:
        """
        Update an existing user fridge notification.
        
        Args:
            model: The UserFridgeNotificationModel with updated values
            
        Raises:
            ClientError: If DynamoDB operation fails
                - ConditionalCheckFailedException if item doesn't exist
                - Other ClientErrors for DynamoDB failures
        """
        dict_format = ufn_model.model_dump(mode="json")
        serialized_data = dict_to_dynamodb(dict_format)
        
        self.db_client.put_item(
            TableName=self.table_name,
            Item=serialized_data,
            ConditionExpression="attribute_exists(userId) AND attribute_exists(fridgeId)"
        )
    
    def delete(self, user_id: str, fridge_id: str) -> bool:
        """
        Delete a user fridge notification.
        
        Args:
            user_id: The user ID
            fridge_id: The fridge ID
            
        Returns:
            True if deleted, False if item didn't exist
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        key = dict_to_dynamodb({"userId": user_id, "fridgeId": fridge_id})
        
        response = self.db_client.delete_item(
            TableName=self.table_name,
            Key=key,
            ReturnValues="ALL_OLD"
        )
        # If Attributes is in response, item existed and was deleted
        return "Attributes" in response
    
    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all notification preferences for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            List of Dict[str, Any]
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        response = self.db_client.query(
            TableName=self.table_name,
            KeyConditionExpression="userId = :userId",
            ExpressionAttributeValues={
                ":userId": {"S": user_id}
            }
        )
        
        items = response.get("Items", [])
        return [dynamodb_to_dict(item) for item in items]
    
    def list_by_fridge(self, fridge_id: str) -> List[Dict[str, Any]]:
        """
        Get all users subscribed to notifications for a specific fridge.
        Uses the FridgeIndex GSI.
        
        Args:
            fridge_id: The fridge ID
            
        Returns:
            List of Dict[str, Any]
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        response = self.db_client.query(
            TableName=self.table_name,
            IndexName="FridgeIndex",
            KeyConditionExpression="fridgeId = :fridgeId",
            ExpressionAttributeValues={
                ":fridgeId": {"S": fridge_id}
            }
        )
        
        items = response.get("Items", [])
        return [dynamodb_to_dict(item) for item in items]
