"""
Repository for querying notification preferences and user details from DynamoDB.
"""
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone
from utils.dynamodb_utils import dynamodb_to_dict
from utils.aws_clients import get_ddb_connection

logger = logging.getLogger()

# Initialize DynamoDB client
dynamodb = get_ddb_connection()
notifications_table = os.environ.get('TABLE_NAME')
users_table = os.environ.get('USERS_TABLE_NAME')
user_devices_table = os.environ.get('USER_DEVICES_TABLE_NAME')


def query_notifications_by_fridge(fridge_id: str) -> List[Dict]:
    """Query all notification preferences for a specific fridge using global index."""
    logger.info(f"Querying notifications for fridgeId: {fridge_id}")
    
    #NOTE: Might want to paginate if there are a lot of users on a fridge, fine for now
    response = dynamodb.query(
        TableName=notifications_table,
        IndexName='FridgeIndex',
        KeyConditionExpression='fridgeId = :fridgeId',
        ExpressionAttributeValues={
            ':fridgeId': {'S': fridge_id}
        }
    )
    
    items = [dynamodb_to_dict(item) for item in response.get('Items', [])]
    logger.info(f"Found {len(items)} notification preferences for fridge {fridge_id}")
    return items


def get_user_details(user_id: str) -> Optional[Dict]:
    """Fetch user email and settings from the user table."""
    #NOTE: Might want to make this an API in the User Service instead of direct DB access
    logger.info(f"Fetching user details for userId: {user_id}")
    
    try:
        response = dynamodb.get_item(
            TableName=users_table,
            Key={'userId': {'S': user_id}},
            ProjectionExpression='email, settings'
        )
        
        if 'Item' not in response:
            # On User Deletion, their notifications will automatically delete.
            # But It's possible that for a few seconds we enter a state where preferences still exist for a deleted user.
            # But in that case we just skip sending notifications to that user
            logger.warning(f"User {user_id} not found in users table")
            return None
            
        return dynamodb_to_dict(response['Item'])
    except Exception as e:
        #For Notifications partial success is better than no success. So just log and skip
        logger.error(f"Error fetching user {user_id}: {e}")
        return None


def get_user_devices(user_id: str) -> List[Dict[str, str]]:
    """Fetch active device records for a user from the user devices table."""
    logger.info(f"Fetching user devices for userId: {user_id}")

    try:
        response = dynamodb.query(
            TableName=user_devices_table,
            KeyConditionExpression='userId = :userId',
            FilterExpression='notificationsEnabled = :enabled AND attribute_not_exists(invalidAt)',
            ExpressionAttributeValues={
                ':userId': {'S': user_id},
                ':enabled': {'BOOL': True},
            },
            ProjectionExpression='installationId, token'
        )

        items = [dynamodb_to_dict(item) for item in response.get('Items', [])]
        devices = [
            {
                'installationId': item.get('installationId'),
                'token': item.get('token'),
            }
            for item in items
            if item.get('installationId') and item.get('token')
        ]
        logger.info(f"Found {len(devices)} active devices for user {user_id}")
        return devices
    except Exception as e:
        #For Notifications partial success is better than no success. So just log and skip
        logger.error(f"Error fetching devices for user {user_id}: {e}")
        return []


def get_user_device_tokens(user_id: str) -> List[str]:
    """Fetch active push notification tokens for a user from the user devices table."""
    devices = get_user_devices(user_id)
    return [device['token'] for device in devices if device.get('token')]


def mark_user_device_invalid(user_id: str, installation_id: str) -> None:
    """Disable a device and set invalidAt timestamp after invalid/unregistered token errors."""
    invalid_at = _utc_now_iso()
    try:
        dynamodb.update_item(
            TableName=user_devices_table,
            Key={
                'userId': {'S': user_id},
                'installationId': {'S': installation_id},
            },
            UpdateExpression='SET notificationsEnabled = :disabled, invalidAt = :invalidAt',
            ExpressionAttributeValues={
                ':disabled': {'BOOL': False},
                ':invalidAt': {'S': invalid_at},
            },
        )
        logger.info(f"Marked installation {installation_id} as invalid for user {user_id}")
    except Exception as e:
        logger.error(f"Error marking installation {installation_id} invalid for user {user_id}: {e}")


def mark_user_device_last_delivered(user_id: str, installation_id: str) -> None:
    """Set lastDeliveredAt after a successful push send."""
    delivered_at = _utc_now_iso()
    try:
        dynamodb.update_item(
            TableName=user_devices_table,
            Key={
                'userId': {'S': user_id},
                'installationId': {'S': installation_id},
            },
            UpdateExpression='SET lastDeliveredAt = :lastDeliveredAt',
            ExpressionAttributeValues={
                ':lastDeliveredAt': {'S': delivered_at},
            },
        )
        logger.info(f"Updated lastDeliveredAt for installation {installation_id} user {user_id}")
    except Exception as e:
        logger.error(f"Error updating lastDeliveredAt for installation {installation_id} user {user_id}: {e}")


def _utc_now_iso() -> str:
    """Generate UTC ISO-8601 timestamp with trailing Z."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
