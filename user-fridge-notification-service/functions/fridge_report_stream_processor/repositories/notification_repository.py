"""
Repository for querying notification preferences and user details from DynamoDB.
"""
import logging
import os
from typing import Dict, List, Optional
from utils.dynamodb_utils import dynamodb_to_dict
from utils.aws_clients import get_ddb_connection

logger = logging.getLogger()

# Initialize DynamoDB client
dynamodb = get_ddb_connection()
notifications_table = os.environ.get('TABLE_NAME')
users_table = os.environ.get('USERS_TABLE_NAME')


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
    """Fetch user email, fcmToken, and settings from user table."""
    #NOTE: Might want to make this an API in the User Service instead of direct DB access
    logger.info(f"Fetching user details for userId: {user_id}")
    
    try:
        response = dynamodb.get_item(
            TableName=users_table,
            Key={'userId': {'S': user_id}},
            ProjectionExpression='email, fcmToken, settings'
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
