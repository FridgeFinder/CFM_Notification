"""
Lambda function to handle user deletion events from EventBridge.
Deletes all notification entries for a deleted user.
"""
import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_ddb_connection():
    """Create a DynamoDB client; uses LocalStack when env is 'local'."""
    env = os.environ.get('DEPLOYMENT_TARGET', 'aws')
    if env == 'aws':
        return boto3.client('dynamodb')
    else:
        return boto3.client('dynamodb', endpoint_url='http://localstack:4566/')

dynamodb = get_ddb_connection()
table_name = os.environ.get('TABLE_NAME')

def lambda_handler(event, context):
    """
    Processes user deletion events and removes all notifications for the user.
    
    Args:
        event: EventBridge event containing userId in the detail
        context: Lambda context object
    
    Returns:
        dict: Summary with userId, totalCount, deletedCount, and failedCount

    Raises:
        Exception: If any deletions failed, triggering EventBridge retry
    """
    logger.info("Received user deletion event", extra={
        "event": event,
        "eventType": "user_deletion"
    })
    
    try:
        # Extract userId from EventBridge event
        user_id = event['detail']['userId']
        logger.info("Starting user notification cleanup", extra={
            "userId": user_id,
            "operation": "delete_user_notifications"
        })
        
        # Query all notifications for this user
        response = dynamodb.query(
            TableName=table_name,
            KeyConditionExpression='userId=:userId',
            ExpressionAttributeValues={
                ':userId': {'S': user_id}
            }
        )
        
        items = response.get('Items', [])
        deleted_count = 0
        failed_count = 0
        total_count = len(items)
        # Delete each notification
        for item in items:
            try:
                dynamodb.delete_item(
                    TableName=table_name,
                    Key={
                        'userId': {'S': item['userId']['S']},
                        'fridgeId': {'S': item['fridgeId']['S']}
                    }
                )
                deleted_count += 1
            except ClientError as e:
                failed_count += 1
                logger.error("Failed to delete notification", extra={
                    "userId": user_id,
                    "fridgeId": item['fridgeId']['S'],
                    "error": str(e),
                    "operation": "delete_notification"
                })
        
        logger.info("User notification cleanup completed", extra={
            "userId": user_id,
            "totalCount": total_count,
            "deletedCount": deleted_count,
            "failedCount": failed_count,
            "operation": "delete_user_notifications",
            "status": "success" if failed_count == 0 else "partial_failure"
        })
        
        # Raise exception if any deletions failed to trigger EventBridge retry
        if failed_count > 0:
            raise Exception(f"Failed to delete {failed_count} of {total_count} notifications for user {user_id}")
        
        return {
            'userId': user_id,
            'totalCount': total_count,
            'deletedCount': deleted_count,
            'failedCount': failed_count
        }
        
    except KeyError as e:
        error_msg = f"Missing required field in event: {str(e)}"
        logger.error("Invalid event structure", extra={
            "error": error_msg,
            "errorType": "KeyError",
            "operation": "delete_user_notifications",
            "status": "failed"
        })
        raise
        
    except Exception as e:
        error_msg = f"Error processing user deletion: {str(e)}"
        logger.error("User deletion processing failed", extra={
            "error": error_msg,
            "errorType": type(e).__name__,
            "operation": "delete_user_notifications",
            "status": "failed"
        })
        raise
