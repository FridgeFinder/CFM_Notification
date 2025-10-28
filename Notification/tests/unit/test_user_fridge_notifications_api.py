import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from Notification.dependencies.python.user_fridge_notifications_api import UserFridgeNotificationApi, ApiResponse
from Notification.dependencies.python.user_fridge_notifications_model import UserFridgeNotificationModel

class TestUserFridgeNotificationApi(unittest.TestCase):
    def setUp(self):
        self.mock_db_client = MagicMock()
        self.api = UserFridgeNotificationApi(db_client=self.mock_db_client)
        self.user_id = "user_1"
        self.fridge_id = "fridge_1"
        self.model = UserFridgeNotificationModel(
            user_id=self.user_id,
            fridge_id=self.fridge_id,
            contact_info={"sms": "+18575678902"},
            contact_types_preferences={
                "sms": {
                    "good": True,
                    "dirty": True,
                    "out_of_order": True,
                    "not_at_location": True,
                    "ghost": True,
                    "food_level_0": True,
                    "food_level_1": True,
                    "food_level_2": True,
                    "food_level_3": True,
                    "cleaned": True
                }
            },
            contact_types_status={"sms": "start"},
        )

    def test_get_user_fridge_notification_found(self):
        # Mock DynamoDB get_item response
        self.mock_db_client.get_item.return_value = {
            "Item": {"user_id": {"S": self.user_id}, "fridge_id": {"S": self.fridge_id}, "contact_info": {"M": {}}}
        }
        with patch("Notification.dependencies.python.user_fridge_notifications_api.dynamodb_to_dict", return_value={"user_id": self.user_id, "fridge_id": self.fridge_id}):
            response = self.api.get_user_fridge_notification(self.user_id, self.fridge_id)
            self.assertEqual(response.status_code, 200)
            self.assertIn("user_id", response.body)

    def test_get_user_fridge_notification_not_found(self):
        self.mock_db_client.get_item.return_value = {}
        response = self.api.get_user_fridge_notification(self.user_id, self.fridge_id)
        self.assertEqual(response.status_code, 404)

    def test_post_user_fridge_notification_success(self):
        self.mock_db_client.put_item.return_value = {}
        mock_dict = {"user_id": self.user_id, "fridge_id": self.fridge_id}
        with patch("Notification.dependencies.python.user_fridge_notifications_api.dict_to_dynamodb", return_value={}), \
             patch("pydantic.BaseModel.model_dump", return_value=mock_dict):
            response = self.api.post_user_fridge_notification(self.model)
            self.assertEqual(response.status_code, 201)

    def test_post_user_fridge_notification_conflict(self):
        self.mock_db_client.exceptions.ConditionalCheckFailedException = ClientError
        self.mock_db_client.put_item.side_effect = ClientError(
            error_response={"Error": {"Code": "ConditionalCheckFailedException"}},
            operation_name="PutItem"
        )
        mock_dict = {"user_id": self.user_id, "fridge_id": self.fridge_id}
        with patch("Notification.dependencies.python.user_fridge_notifications_api.dict_to_dynamodb", return_value={}), \
             patch("pydantic.BaseModel.model_dump", return_value=mock_dict):
            response = self.api.post_user_fridge_notification(self.model)
            self.assertEqual(response.status_code, 409)

    def test_put_user_fridge_notification_not_found(self):
        self.mock_db_client.get_item.return_value = {}
        response = self.api.put_user_fridge_notification(self.model)
        self.assertEqual(response.status_code, 404)

    def test_put_user_fridge_notification_success(self):
        self.mock_db_client.get_item.return_value = {"Item": {"created_at": datetime.now(timezone.utc).isoformat()}}
        self.mock_db_client.put_item.return_value = {}
        mock_dict = {"user_id": self.user_id, "fridge_id": self.fridge_id}
        with patch("Notification.dependencies.python.user_fridge_notifications_api.dynamodb_to_dict", return_value={"created_at": datetime.now(timezone.utc).isoformat()}), \
             patch("pydantic.BaseModel.model_dump", return_value=mock_dict):
            response = self.api.put_user_fridge_notification(self.model)
            self.assertEqual(response.status_code, 200)

    def test_post_user_fridge_notification_db_error(self):
        error = ClientError(
            error_response={"Error": {"Code": "InternalServerError", "Message": "Database Error"}},
            operation_name="PutItem"
        )
        self.mock_db_client.put_item.side_effect = error
        mock_dict = {"user_id": self.user_id, "fridge_id": self.fridge_id}
        with patch("Notification.dependencies.python.user_fridge_notifications_api.dict_to_dynamodb", return_value={}), \
            patch("pydantic.BaseModel.model_dump", return_value=mock_dict):
            response = self.api.post_user_fridge_notification(self.model)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.body, {"message": "Database Error"})

    def test_put_user_fridge_notification_db_error(self):
        # Simulate existing item returned by get_item
        self.mock_db_client.get_item.return_value = {"Item": {"created_at": datetime.now(timezone.utc).isoformat()}}
        # Simulate DynamoDB put_item raising a ClientError
        error = ClientError(
            error_response={"Error": {"Code": "InternalServerError", "Message": "Database Error"}},
            operation_name="PutItem"
        )
        self.mock_db_client.put_item.side_effect = error
        mock_dict = {"user_id": self.user_id, "fridge_id": self.fridge_id}
        with patch("Notification.dependencies.python.user_fridge_notifications_api.dynamodb_to_dict", return_value={"created_at": datetime.now(timezone.utc).isoformat()}), \
             patch("pydantic.BaseModel.model_dump", return_value=mock_dict):
            response = self.api.put_user_fridge_notification(self.model)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.body, {"message": "Database Error"})

    def test_race_condition_put(self):
        # Setup
        api = UserFridgeNotificationApi(db_client=MagicMock())
        user_id = "user1"
        fridge_id = "fridge1"
        updated_at = "2025-10-28T12:00:00Z"
        item = {
            "user_id": {"S": user_id},
            "fridge_id": {"S": fridge_id},
            "updated_at": {"S": updated_at}
        }
        # Mock get_item to return the same updated_at for both calls
        api.db_client.get_item.return_value = {"Item": item}

        # First put_item succeeds
        api.db_client.put_item.return_value = {}

        # Second put_item raises ConditionalCheckFailedException
        def put_item_side_effect(*args, **kwargs):
            if hasattr(put_item_side_effect, "called"):
                raise ClientError(
                    {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
                )
            put_item_side_effect.called = True
            return {}
        api.db_client.put_item.side_effect = put_item_side_effect

        # Prepare model
        model = MagicMock()
        model.user_id = user_id
        model.fridge_id = fridge_id
        model.model_dump.return_value = {"user_id": user_id, "fridge_id": fridge_id, "updated_at": updated_at}

        # First update should succeed
        response1 = api.put_user_fridge_notification(model)
        self.assertEqual(response1.status_code, 200)

        # Second update should fail with conflict
        response2 = api.put_user_fridge_notification(model)
        self.assertEqual(response2.status_code, 409)
        self.assertIn("Update conflict, please retry", response2.body["message"])

if __name__ == "__main__":
    unittest.main()
