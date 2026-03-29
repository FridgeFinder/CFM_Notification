import json
import unittest
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

from user_fridge_notifications_service import UserFridgeNotificationService
from user_fridge_notifications_model import UserFridgeNotificationModel


class TestUserFridgeNotificationService(unittest.TestCase):
    def setUp(self):
        self.mock_repository = MagicMock()
        self.service = UserFridgeNotificationService(repository=self.mock_repository)
        self.user_id = "user_1"
        self.fridge_id = "fridge_1"
        self.sms_prefs = {
            "good": True,
            "dirty": True,
            "outOfOrder": True,
            "notAtLocation": True,
            "ghost": True,
            "noFood": True,
            "hasFood": True,
        }
        self.item_dict = {
            "userId": self.user_id,
            "fridgeId": self.fridge_id,
            "contactTypePreferences": {"email": self.sms_prefs},
        }
        self.model = UserFridgeNotificationModel(
            userId=self.user_id,
            fridgeId=self.fridge_id,
            contactTypePreferences={"email": self.sms_prefs},
        )

    # --- GET ---

    def test_get_user_fridge_notification_found(self):
        self.mock_repository.get.return_value = self.item_dict
        response = self.service.get_user_fridge_notification(self.user_id, self.fridge_id)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["userId"], self.user_id)
        self.assertEqual(body["fridgeId"], self.fridge_id)

    def test_get_user_fridge_notification_not_found(self):
        self.mock_repository.get.return_value = None
        response = self.service.get_user_fridge_notification(self.user_id, self.fridge_id)
        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "Item not found")
        self.assertEqual(body["error"]["code"], "ITEM_NOT_FOUND")

    # --- POST ---

    def test_post_user_fridge_notification_success(self):
        self.mock_repository.create.return_value = None
        response = self.service.post_user_fridge_notification(self.model)
        self.assertEqual(response["statusCode"], 201)
        body = json.loads(response["body"])
        self.assertEqual(body["userId"], self.user_id)
        self.assertEqual(body["fridgeId"], self.fridge_id)

    def test_post_user_fridge_notification_conflict(self):
        self.mock_repository.create.side_effect = ClientError(
            error_response={"Error": {"Code": "ConditionalCheckFailedException"}},
            operation_name="PutItem",
        )
        response = self.service.post_user_fridge_notification(self.model)
        self.assertEqual(response["statusCode"], 409)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "UserFridgeNotification with userId: user_1, and fridgeId: fridge_1 already exists")
        self.assertEqual(body["error"]["code"], "ITEM_ALREADY_EXISTS")

    def test_post_user_fridge_notification_db_error(self):
        self.mock_repository.create.side_effect = ClientError(
            error_response={"Error": {"Code": "InternalServerError", "Message": "Database Error"}},
            operation_name="PutItem",
        )
        with self.assertRaises(ClientError):
            self.service.post_user_fridge_notification(self.model)

    # --- PATCH ---

    def test_patch_user_fridge_notification_success(self):
        self.mock_repository.get.return_value = self.item_dict
        self.mock_repository.update.return_value = None
        new_prefs = {"email": {k: False for k in self.sms_prefs}}
        response = self.service.patch_user_fridge_notification(
            self.user_id, self.fridge_id, new_prefs
        )
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertFalse(body["contactTypePreferences"]["email"]["good"])

    def test_patch_user_fridge_notification_not_found(self):
        self.mock_repository.get.return_value = None
        response = self.service.patch_user_fridge_notification(
            self.user_id, self.fridge_id, {"email": self.sms_prefs}
        )
        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "User Fridge Notification not found")
        self.assertEqual(body["error"]["code"], "ITEM_NOT_FOUND")

    def test_patch_user_fridge_notification_db_error(self):
        self.mock_repository.get.return_value = self.item_dict
        self.mock_repository.update.side_effect = ClientError(
            error_response={"Error": {"Code": "InternalServerError", "Message": "Database Error"}},
            operation_name="PutItem",
        )
        with self.assertRaises(ClientError):
            self.service.patch_user_fridge_notification(
                self.user_id, self.fridge_id, {"email": {k: False for k in self.sms_prefs}}
            )

    def test_patch_update_conflict_returns_not_found(self):
        """ConditionalCheckFailedException on update means item was deleted concurrently."""
        self.mock_repository.get.return_value = self.item_dict
        self.mock_repository.update.side_effect = ClientError(
            error_response={"Error": {"Code": "ConditionalCheckFailedException"}},
            operation_name="PutItem",
        )
        response = self.service.patch_user_fridge_notification(
            self.user_id, self.fridge_id, {"email": {k: False for k in self.sms_prefs}}
        )
        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "User Fridge Notification not found")
        self.assertEqual(body["error"]["code"], "ITEM_NOT_FOUND")

    # --- DELETE ---

    def test_delete_user_fridge_notification_success(self):
        self.mock_repository.delete.return_value = True
        response = self.service.delete_user_fridge_notification(self.user_id, self.fridge_id)
        self.assertEqual(response["statusCode"], 204)

    def test_delete_user_fridge_notification_not_found(self):
        self.mock_repository.delete.return_value = False
        response = self.service.delete_user_fridge_notification(self.user_id, self.fridge_id)
        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "User Fridge Notification not found")
        self.assertEqual(body["error"]["code"], "ITEM_NOT_FOUND")