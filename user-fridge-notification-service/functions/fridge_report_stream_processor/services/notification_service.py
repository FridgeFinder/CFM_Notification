"""
Notification service for sending email and push notifications.
"""
import logging
from typing import Optional
import firebase_admin
from firebase_admin import messaging
from utils.aws_clients import get_ses_connection
from constants import CONDITION_MESSAGE_MAP, FOOD_LEVEL_MESSAGE_MAP

logger = logging.getLogger()

# Initialize SES client
ses = get_ses_connection()


def send_email_notification(pref: dict, email: str, fridge_id: str, formated_fridge_condition: str, formated_food_condition: str, food_level: int):
    """Send email notification via SES."""
    try:
        formated_alert = get_notification_message(pref, formated_fridge_condition, formated_food_condition, food_level)
        if not formated_alert:
            logger.info(f"User {email} does not want email notifications for this condition/food level")
            return
        subject = f"FridgeFinder Alert: {fridge_id} - {formated_alert}"
        body = f"""    
        Hello, a fridge you are subscribed to has an update:

        Fridge ID: {fridge_id}
        Update: {formated_alert}
        
        Please check the Fridge Finder app for more details: https://www.fridgefinder.app/fridge/{fridge_id}

        ---
        Unsubscribe: https://www.fridgefinder.app/unsubscribe?token=eyJhbGciOiJ
        """

        ses.send_email(
            Source='fridge_alerts@fridgefinder.app',  # Update with your verified SES email
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        logger.info(f"Email sent successfully to {email}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")


def send_push_notification(pref: dict, fcm_token: str, fridge_id: str, formated_fridge_condition: str, formated_food_condition: str, food_level: int):
    """Send push notification via Firebase Cloud Messaging."""
    if not firebase_admin._apps:
        logger.warning('Firebase not initialized, skipping push notification')
        return
    
    try:
        message = get_notification_message(pref, formated_fridge_condition, formated_food_condition, food_level)
        if not message:
            logger.info(f'User does not want push notifications for this condition/food level')
            return
        
        message = messaging.Message(
            notification=messaging.Notification(
                title=fridge_id,
                body=message
            ),
            token=fcm_token,
        )
        
        response = messaging.send(message)
        logger.info(f'Push notification sent successfully. Response: {response}')
        
    except messaging.UnregisteredError:
        logger.warning(f'FCM token is invalid or unregistered: {fcm_token[:20]}...')
        # TODO: Mark token as invalid in user table
    except messaging.SenderIdMismatchError:
        logger.error(f'FCM token belongs to different Firebase project')
    except Exception as e:
        logger.error(f'Failed to send push notification: {e}', exc_info=True)


def get_notification_message(contact_prefs: dict, formatted_fridge_condition: str, formated_food_condition: str, food_level: Optional[int]):
    """Generate notification message based on user preferences and fridge condition."""
    condition_pref = contact_prefs.get(formatted_fridge_condition, False)
    food_condition_pref = contact_prefs.get(formated_food_condition, False)
    condition_message = CONDITION_MESSAGE_MAP.get(formatted_fridge_condition)
    food_message = FOOD_LEVEL_MESSAGE_MAP.get(food_level)
    if condition_pref and food_condition_pref:
        return f"{condition_message}, and {food_message}"
    elif condition_pref:
        return condition_message
    elif food_condition_pref:
        return food_message
    else:
        return None
