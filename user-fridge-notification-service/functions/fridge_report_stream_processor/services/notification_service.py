"""
Notification service for sending email and push notifications.
"""
import logging
import os
from typing import Optional
import firebase_admin
from firebase_admin import messaging
from utils.aws_clients import get_ses_connection
from constants import CONDITION_MESSAGE_MAP, FOOD_LEVEL_MESSAGE_MAP

logger = logging.getLogger()

# Initialize SES client
ses = get_ses_connection()

# Get environment for URL construction
environment = os.environ.get('ENVIRONMENT', 'dev')
base_url = "https://www.fridgefinder.app" if environment == 'prod' else f"https://{environment}.fridgefinder.app"


def send_email_notification(pref: dict, email: str, fridge_id: str, formated_fridge_condition: str, formated_food_condition: str, food_level: int):
    """Send email notification via SES."""
    try:
        formated_alert = get_notification_message(pref, formated_fridge_condition, formated_food_condition, food_level)
        if not formated_alert:
            logger.info(f"User {email} does not want email notifications for this condition/food level")
            return
        
        # Map conditions to emojis
        emoji_map = {
            'good': '✅',
            'dirty': '🧹',
            'outOfOrder': '⚠️',
            'notAtLocation': '📍',
            'ghost': '👻'
        }
        condition_emoji = emoji_map.get(formated_fridge_condition, '📢')
        
        subject = f"{condition_emoji} FridgeFinder Alert: {fridge_id}"
        
        # HTML email body with inline CSS for email client compatibility
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
            <table role="presentation" style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 20px 0;">
                        <table role="presentation" style="width: 100%; max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <!-- Header with Logo -->
                            <tr>
                                <td style="padding: 30px 20px; text-align: center; background: linear-gradient(135deg, #88B3FF 0%, #6B9FFF 100%); border-radius: 8px 8px 0 0;">
                                    <img src="https://fridgefinder-assets.s3.amazonaws.com/email/logo.png" alt="FridgeFinder" style="max-width: 112px; height: auto; display: block; margin: 0 auto;" />
                                </td>
                            </tr>
                            
                            <!-- Main Content -->
                            <tr>
                                <td style="padding: 40px 30px;">
                                    <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px; line-height: 1.5;">
                                        Hi! 👋
                                    </p>
                                    <p style="margin: 0 0 25px 0; color: #333333; font-size: 16px; line-height: 1.5;">
                                        A fridge you're following has a status update:
                                    </p>
                                    
                                    <!-- Alert Box -->
                                    <table role="presentation" style="width: 100%; background-color: #f8f9fa; border-left: 4px solid #88B3FF; border-radius: 4px; margin-bottom: 25px;">
                                        <tr>
                                            <td style="padding: 20px;">
                                                <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                                                    Fridge ID
                                                </p>
                                                <p style="margin: 0 0 15px 0; color: #333333; font-size: 18px; font-weight: 600;">
                                                    {fridge_id}
                                                </p>
                                                <p style="margin: 0 0 5px 0; color: #666666; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                                                    Update
                                                </p>
                                                <p style="margin: 0; color: #333333; font-size: 16px;">
                                                    {formated_alert}
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <!-- CTA Button -->
                                    <table role="presentation" style="margin: 0 auto;">
                                        <tr>
                                            <td style="border-radius: 25px; background: #5B8FEE; box-shadow: 0 4px 6px rgba(91, 143, 238, 0.4);">
                                                <a href="{base_url}/fridge/{fridge_id}" style="display: inline-block; padding: 16px 48px; color: #ffffff; text-decoration: none; font-weight: 600; font-size: 16px; letter-spacing: 0.5px;">
                                                    View Status Update
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="padding: 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center;">
                                    <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;">
                                        Stay connected with your community fridges 🍏
                                    </p>                                    
                                    <!-- App Store Buttons -->
                                    <table role="presentation" style="margin: 0 auto 12px auto;">
                                        <tr>
                                            <td style="padding: 0 5px;">
                                                <a href="https://apps.apple.com/app/YOUR_APP_ID" style="display: inline-block;">
                                                    <img src="https://developer.apple.com/assets/elements/badges/download-on-the-app-store.svg" alt="Download on the App Store" style="height: 45px; width: auto;" />
                                                </a>
                                            </td>
                                            <td style="padding: 0 5px;">
                                                <a href="https://play.google.com/store/apps/details?id=YOUR_PACKAGE_NAME" style="display: inline-block;">
                                                    <img src="https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png" alt="Get it on Google Play" style="height: 63px; width: auto;" />
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                                                        <p style="margin: 0 0 15px 0; color: #999999; font-size: 11px; line-height: 1.4;">
                                        This is an automated notification. Please do not reply to this email.
                                    </p>
                                    <p style="margin: 0 0 15px 0; color: #999999; font-size: 11px; line-height: 1.4;">
                                        You received this because you subscribed to updates for this community fridge.
                                    </p>
                                    <p style="margin: 0 0 15px 0; color: #999999; font-size: 12px;">
                                        <a href="{base_url}/preferences" style="color: #88B3FF; text-decoration: none;">Manage Preferences</a>
                                        &nbsp;|&nbsp;
                                        <a href="{base_url}/privacy" style="color: #88B3FF; text-decoration: none;">Privacy Policy</a>
                                        &nbsp;|&nbsp;
                                        <a href="{base_url}/support" style="color: #88B3FF; text-decoration: none;">Contact Support</a>
                                        &nbsp;|&nbsp;
                                        <a href="{base_url}/unsubscribe?token=eyJhbGciOiJ" style="color: #88B3FF; text-decoration: none;">Unsubscribe</a>
                                    </p>
                                    <p style="margin: 0; color: #999999; font-size: 11px;">
                                        © 2026 FridgeFinder. All rights reserved.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # Plain text fallback for email clients that don't support HTML
        text_body = f"""
        Hi!
        
        A fridge you're following has a status update:
        
        Fridge ID: {fridge_id}
        Update: {formated_alert}
        
        View details: {base_url}/fridge/{fridge_id}
        
        Stay connected with your local community fridges!
        
        ---
        Unsubscribe: {base_url}/unsubscribe?token=eyJhbGciOiJ
        """

        ses.send_email(
            Source='fridge_alerts@fridgefinder.app',
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Text': {'Data': text_body},
                    'Html': {'Data': html_body}
                }
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
            logger.info('User does not want push notifications for this condition/food level')
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
        logger.error('FCM token belongs to different Firebase project')
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
