import logging
from typing import Dict, Any

# Local imports
from constants import CONDITION_MAP, FOOD_LEVEL_NOTIFICATION_MAP
from utils.firebase_client import initialize_firebase
from repositories.notification_repository import query_notifications_by_fridge, get_user_details
from services.notification_service import send_email_notification, send_push_notification

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Firebase when module is loaded
initialize_firebase()

def process_fridge_report(fridge_id: str, fridge_condition: str, food_level: int):
    """Process a fridge report and send notifications to subscribed users."""
    logger.info(f"Processing fridge report - ID: {fridge_id}, Condition: {fridge_condition}, Food Level: {food_level}")
    
    # Query all users subscribed to this fridge
    notification_prefs = query_notifications_by_fridge(fridge_id)
    formated_fridge_condition = CONDITION_MAP.get(fridge_condition)
    formated_food_condition = FOOD_LEVEL_NOTIFICATION_MAP.get(food_level)
    if not formated_fridge_condition or not formated_food_condition:
        # It's possible we add a new condition or food level in the Status Report service 
        # that the notification service does not yet support
        logger.warning(f"Invalid condition or food level in record")
        return

    for pref in notification_prefs:
        user_id = pref.get('userId')
        # Get user details
        user = get_user_details(user_id)
        if not user:
            logger.error(f"Skipping notification - user details not found for user ID: {user_id}")
            continue
        
        # Extract user settings, each one has their own thing so it makes sense.. 
        settings = user.get('settings', {})
        email_enabled = settings.get('emailNotificationEnabled', False)
        push_enabled = settings.get('pushNotificationEnabled', False)
        ######
        if email_enabled:
            email = user.get('email')
            if email:
                email_prefs = (pref.get('contactTypePreferences') or {}).get('email')
                if email_prefs:
                    send_email_notification(email_prefs, email, fridge_id, formated_fridge_condition, formated_food_condition, food_level)
                else:
                    logger.info(f"User {user_id} has no email notification preferences configured")
            else:
                logger.info(f"User {user_id} has email notifications enabled but no email found")
        else:
            logger.info(f"User {user_id} has email notifications disabled")
        
        # Check and send push notification
        if push_enabled:
            fcm_token = user.get('fcmToken')
            if fcm_token:
                device_prefs = (pref.get('contactTypePreferences') or {}).get('device')
                if device_prefs:
                    send_push_notification(device_prefs, fcm_token, fridge_id, formated_fridge_condition, formated_food_condition, food_level)
                else:
                    logger.info(f"User {user_id} has no device notification preferences configured")
            else:
                logger.info(f"User {user_id} has push notifications enabled but no FCM token found")
        else:
            logger.info(f"User {user_id} has push notifications disabled")


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Process DynamoDB Stream events from FridgeReportStream.
    Sends notifications to users based on their preferences.
    Args:
        event: DynamoDB Stream event
        context: Lambda context
    Returns:
        Dict with processing status
    """
    logger.info(f"Processing {len(event.get('Records', []))} records from DynamoDB Stream")
    
    processed_count = 0
    
    for record in event.get('Records', []):
        try:
            # Only process INSERT events
            event_name = record.get('eventName', '')
            if event_name != 'INSERT':
                logger.info(f"Skipping non-INSERT event: {event_name}")
                continue
            
            # Get the new image data
            dynamodb_data = record.get('dynamodb', {})
            new_image = dynamodb_data.get('NewImage', {})
            
            if not new_image:
                logger.warning(f"No new image found in record")
                continue
            
            # Extract required fields using TypeDeserializer
            fridge_id = new_image.get('fridgeId', {}).get('S')
            condition = new_image.get('condition', {}).get('S')
            food_level = new_image.get('foodPercentage', {}).get('N')
            
            if not fridge_id or not condition or not food_level:
                #Note: Should not get here, all of these fields are required to make a status report
                logger.warning(f"Missing required fields in record")
                continue

            # Process the fridge report
            process_fridge_report(fridge_id, condition, int(food_level))
            processed_count += 1
            
        except Exception as e:
            #For notifications, duplicates are worse than missing one, just log and continue
            logger.error(f"Error processing record: {e}", exc_info=True)
    
    return {
        'message': 'Successfully processed fridge reports',
        'records_processed': processed_count
    }

