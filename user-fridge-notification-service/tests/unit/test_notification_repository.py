"""Unit tests for functions/fridge_report_stream_processor/repositories/notification_repository.py"""
import unittest
from unittest.mock import patch

from repositories import notification_repository

# DynamoDB wire-format items returned by mocked queries.
_DDB_NOTIFICATION = {
    "fridgeId": {"S": "fridge_1"},
    "userId": {"S": "user_1"},
}

_DDB_USER = {
    "email": {"S": "user@example.com"},
    "fcmToken": {"S": "token_abc"},
    "settings": {
        "M": {
            "emailNotificationEnabled": {"BOOL": True},
            "pushNotificationEnabled": {"BOOL": False},
        }
    },
}


class TestQueryNotificationsByFridge(unittest.TestCase):
    def test_returns_deserialized_items(self):
        with patch.object(notification_repository, "dynamodb") as mock_db, \
             patch.object(notification_repository, "notifications_table", "NotifTable"):
            mock_db.query.return_value = {"Items": [_DDB_NOTIFICATION]}
            result = notification_repository.query_notifications_by_fridge("fridge_1")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["fridgeId"], "fridge_1")
        self.assertEqual(result[0]["userId"], "user_1")

    def test_returns_empty_list_when_no_subscribers(self):
        with patch.object(notification_repository, "dynamodb") as mock_db, \
             patch.object(notification_repository, "notifications_table", "NotifTable"):
            mock_db.query.return_value = {"Items": []}
            result = notification_repository.query_notifications_by_fridge("fridge_1")

        self.assertEqual(result, [])

    def test_queries_fridge_index_gsi(self):
        with patch.object(notification_repository, "dynamodb") as mock_db, \
             patch.object(notification_repository, "notifications_table", "NotifTable"):
            mock_db.query.return_value = {"Items": []}
            notification_repository.query_notifications_by_fridge("fridge_1")

        call_kwargs = mock_db.query.call_args[1]
        self.assertEqual(call_kwargs["IndexName"], "FridgeIndex")

    def test_filters_by_fridge_id(self):
        with patch.object(notification_repository, "dynamodb") as mock_db, \
             patch.object(notification_repository, "notifications_table", "NotifTable"):
            mock_db.query.return_value = {"Items": []}
            notification_repository.query_notifications_by_fridge("specific_fridge")

        call_kwargs = mock_db.query.call_args[1]
        self.assertEqual(
            call_kwargs["ExpressionAttributeValues"][":fridgeId"]["S"], "specific_fridge"
        )

    def test_returns_multiple_subscribers(self):
        item2 = {"fridgeId": {"S": "fridge_1"}, "userId": {"S": "user_2"}}
        with patch.object(notification_repository, "dynamodb") as mock_db, \
             patch.object(notification_repository, "notifications_table", "NotifTable"):
            mock_db.query.return_value = {"Items": [_DDB_NOTIFICATION, item2]}
            result = notification_repository.query_notifications_by_fridge("fridge_1")

        self.assertEqual(len(result), 2)


class TestGetUserDetails(unittest.TestCase):
    def test_returns_deserialized_user_dict_when_found(self):
        with patch.object(notification_repository, "dynamodb") as mock_db, \
             patch.object(notification_repository, "users_table", "UsersTable"):
            mock_db.get_item.return_value = {"Item": _DDB_USER}
            result = notification_repository.get_user_details("user_1")

        self.assertIsNotNone(result)
        self.assertEqual(result["email"], "user@example.com")
        self.assertEqual(result["fcmToken"], "token_abc")

    def test_returns_none_when_user_not_found(self):
        with patch.object(notification_repository, "dynamodb") as mock_db, \
             patch.object(notification_repository, "users_table", "UsersTable"):
            mock_db.get_item.return_value = {}
            result = notification_repository.get_user_details("user_1")

        self.assertIsNone(result)

    def test_returns_none_on_exception(self):
        with patch.object(notification_repository, "dynamodb") as mock_db, \
             patch.object(notification_repository, "users_table", "UsersTable"):
            mock_db.get_item.side_effect = Exception("DB unavailable")
            result = notification_repository.get_user_details("user_1")

        self.assertIsNone(result)

    def test_queries_correct_user_id(self):
        with patch.object(notification_repository, "dynamodb") as mock_db, \
             patch.object(notification_repository, "users_table", "UsersTable"):
            mock_db.get_item.return_value = {}
            notification_repository.get_user_details("specific_user")

        call_kwargs = mock_db.get_item.call_args[1]
        self.assertEqual(call_kwargs["Key"]["userId"]["S"], "specific_user")