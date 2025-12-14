from xml.parsers.expat import model
from botocore.exceptions import ClientError
from pydantic import ValidationError
import logging

try:
    # Preferred: relative import when running inside SAM/local container
    from user_fridge_notifications_model import UserFridgeNotificationModel
    from user_fridge_notifications_repository import UserFridgeNotificationRepository
    from response_utils import error_response, success_response, ErrorCode
except ModuleNotFoundError:
    # Fallback: absolute import when package is installed for tests
    from Notification.dependencies.python.user_fridge_notifications_model import UserFridgeNotificationModel
    from Notification.dependencies.python.user_fridge_notifications_repository import UserFridgeNotificationRepository
    from Notification.dependencies.python.response_utils import error_response, success_response, ErrorCode

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class UserFridgeNotificationService:
    """Service layer for user fridge notification business logic"""
    
    def __init__(self, repository: UserFridgeNotificationRepository):
        self.repository = repository

    def get_user_fridge_notification(self, userId: str, fridgeId: str, request_id: str = None) -> dict:
        """Get user fridge notification preferences (returns plain dict)."""
        ufn_dict = self.repository.get(userId, fridgeId)
        
        if ufn_dict is None:
            return error_response(404, "Item not found", ErrorCode.NOT_FOUND, request_id=request_id)
        return success_response(200, ufn_dict, request_id=request_id)

    def post_user_fridge_notification(self, user_notification_model: UserFridgeNotificationModel, request_id: str = None) -> dict:
        """Create new user fridge notification preferences"""
        try:
            self.repository.create(user_notification_model)
            logger.info(
                "User fridge notification created successfully",
                extra={
                    "request_id": request_id,
                    "userId": user_notification_model.userId,
                    "fridgeId": user_notification_model.fridgeId,
                    "operation": "create_user_fridge_notification",
                }
            )
            return success_response(201, user_notification_model.model_dump(mode="json"), request_id=request_id)
        except ClientError as e:
            if e.response['Error'].get('Code') == "ConditionalCheckFailedException":
                error_message = f"UserFridgeNotification with userId: {user_notification_model.userId}, and fridgeId: {user_notification_model.fridgeId} already exists"
                return error_response(409, error_message, ErrorCode.ALREADY_EXISTS, request_id=request_id)
            raise

    def patch_user_fridge_notification(self, userId: str, fridgeId: str, contactTypePreferences: dict, request_id: str = None) -> dict:
        """
        Partially update existing user fridge notification preferences.
        
        Args:
            userId: The user ID
            fridgeId: The fridge ID
            contactTypePreferences: New contact type preferences to update
            request_id: The request ID for tracing
            
        Returns:
            API Gateway formatted response dict
        """
        try:
            # Fetch existing item (dict)
            ufn_dict = self.repository.get(userId, fridgeId)
            
            if ufn_dict is None:
                return error_response(
                    404, "User Fridge Notification not found", 
                    ErrorCode.NOT_FOUND,
                    request_id=request_id
                )
            
            # Convert to model to leverage validation and helper, update preferences
            ufn_model = UserFridgeNotificationModel(**ufn_dict)
            ufn_model.patch_preferences(contactTypePreferences)
            
            # Save updated model
            self.repository.update(ufn_model)
            return success_response(200, ufn_model.model_dump(mode="json"), request_id=request_id)
        except ValidationError as ve:
            # Pydantic validation error when validating contactTypePreferences
            return error_response(400, str(ve), ErrorCode.VALIDATION_ERROR, request_id=request_id)
        except ClientError as e:
            if e.response['Error'].get('Code') == "ConditionalCheckFailedException":
                # Super Duper Unlikely: Item was deleted between get and update
                return error_response(404, "User Fridge Notification not found", ErrorCode.NOT_FOUND, request_id=request_id)
            raise

    def get_all_user_notifications(self, userId: str, request_id: str = None) -> dict:
        """
        Get all notification preferences for a user across all fridges.
        
        Args:
            userId: The user ID
            request_id: The request ID for tracing
            
        Returns:
            API Gateway formatted response dict with list of notifications
        """
        notifications = self.repository.list_by_user(userId)
        return success_response(200, {"notifications": notifications, "count": len(notifications)}, request_id=request_id)

    def delete_user_fridge_notification(self, userId: str, fridgeId: str, request_id: str = None) -> dict:
        """
        Delete user fridge notification preferences.
        
        Args:
            userId: The user ID
            fridgeId: The fridge ID
            request_id: The request ID for tracing
            
        Returns:
            API Gateway formatted response dict
        """
        deleted = self.repository.delete(userId, fridgeId)
        
        if not deleted:
            return error_response(404, "User Fridge Notification not found", ErrorCode.NOT_FOUND, request_id=request_id)
        return success_response(204, None, request_id=request_id)

