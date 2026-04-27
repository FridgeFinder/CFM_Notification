"""Unit tests for functions/fridge_notifications/user/user_fridge_notifications_repository.py"""
import unittest
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

from user_fridge_notifications_model import UserFridgeNotificationModel
from user_fridge_notifications_repository import UserFridgeNotificationRepository

# A valid DynamoDB wire-format notification item used in multiple tests.
_DDB_ITEM = {
    "userId": {"S": "user_1"},
    "fridgeId": {"S": "fridge_1"},
    "contactTypePreferences": {
        "M": {
            "email": {
                "M": {
                    "good": {"BOOL": True},
                    "dirty": {"BOOL": False},
                    "outOfOrder": {"BOOL": False},
                    "notAtLocation": {"BOOL": False},
                    "ghost": {"BOOL": False},
                    "noFood": {"BOOL": True},
                    "hasFood": {"BOOL": False},
                }
            }
        }
    },
    "createdAt": {"S": "2024-01-01T00:00:00+00:00"},
    "updatedAt": {"S": "2024-01-01T00:00:00+00:00"},
}

_ALL_TRUE_PREFS = {
    "good": True,
    "dirty": True,
    "outOfOrder": True,
    "notAtLocation": True,
    "ghost": True,
    "noFood": True,
    "hasFood": True,
}


def _make_model(user_id="user_1", fridge_id="fridge_1"):
    return UserFridgeNotificationModel(
        userId=user_id,
        fridgeId=fridge_id,
        contactTypePreferences={"email": _ALL_TRUE_PREFS},
    )


class TestUserFridgeNotificationRepositoryGet(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.repo = UserFridgeNotificationRepository(self.mock_db, "TestTable")

    def test_returns_deserialized_dict_when_item_found(self):
        self.mock_db.get_item.return_value = {"Item": _DDB_ITEM}
        result = self.repo.get("user_1", "fridge_1")
        self.assertIsNotNone(result)
        self.assertEqual(result["userId"], "user_1")
        self.assertEqual(result["fridgeId"], "fridge_1")

    def test_returns_none_when_item_not_found(self):
        self.mock_db.get_item.return_value = {}
        self.assertIsNone(self.repo.get("user_1", "fridge_1"))

    def test_uses_correct_table_name(self):
        self.mock_db.get_item.return_value = {}
        self.repo.get("user_1", "fridge_1")
        self.assertEqual(self.mock_db.get_item.call_args[1]["TableName"], "TestTable")

    def test_propagates_client_error(self):
        self.mock_db.get_item.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "DB error"}}, "GetItem"
        )
        with self.assertRaises(ClientError):
            self.repo.get("user_1", "fridge_1")


class TestUserFridgeNotificationRepositoryCreate(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.repo = UserFridgeNotificationRepository(self.mock_db, "TestTable")

    def test_calls_put_item_with_correct_table(self):
        self.repo.create(_make_model())
        self.assertEqual(self.mock_db.put_item.call_args[1]["TableName"], "TestTable")

    def test_condition_expression_requires_item_not_exist(self):
        self.repo.create(_make_model())
        condition = self.mock_db.put_item.call_args[1]["ConditionExpression"]
        self.assertIn("attribute_not_exists", condition)

    def test_propagates_conditional_check_failed_exception(self):
        self.mock_db.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
        )
        with self.assertRaises(ClientError):
            self.repo.create(_make_model())

    def test_propagates_other_client_errors(self):
        self.mock_db.put_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": ""}},
            "PutItem",
        )
        with self.assertRaises(ClientError):
            self.repo.create(_make_model())


class TestUserFridgeNotificationRepositoryUpdate(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.repo = UserFridgeNotificationRepository(self.mock_db, "TestTable")

    def test_calls_put_item_with_correct_table(self):
        self.repo.update(_make_model())
        self.assertEqual(self.mock_db.put_item.call_args[1]["TableName"], "TestTable")

    def test_condition_expression_requires_item_to_exist(self):
        self.repo.update(_make_model())
        condition = self.mock_db.put_item.call_args[1]["ConditionExpression"]
        self.assertIn("attribute_exists", condition)

    def test_propagates_conditional_check_failed_exception(self):
        self.mock_db.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
        )
        with self.assertRaises(ClientError):
            self.repo.update(_make_model())


class TestUserFridgeNotificationRepositoryDelete(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.repo = UserFridgeNotificationRepository(self.mock_db, "TestTable")

    def test_returns_true_when_item_was_deleted(self):
        self.mock_db.delete_item.return_value = {"Attributes": _DDB_ITEM}
        self.assertTrue(self.repo.delete("user_1", "fridge_1"))

    def test_raises_when_item_does_not_exist(self):
        # DynamoDB raises ConditionalCheckFailedException when condition fails
        self.mock_db.delete_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "DeleteItem"
        )
        with self.assertRaises(ClientError):
            self.repo.delete("user_1", "fridge_1")

    def test_uses_correct_table_name(self):
        self.mock_db.delete_item.return_value = {"Attributes": _DDB_ITEM}
        self.repo.delete("user_1", "fridge_1")
        self.assertEqual(self.mock_db.delete_item.call_args[1]["TableName"], "TestTable")


class TestUserFridgeNotificationRepositoryListByFridge(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.repo = UserFridgeNotificationRepository(self.mock_db, "TestTable")

    def test_queries_fridge_index_gsi(self):
        self.mock_db.query.return_value = {"Items": []}
        self.repo.list_by_fridge("fridge_1")
        self.assertEqual(self.mock_db.query.call_args[1]["IndexName"], "FridgeIndex")

    def test_returns_deserialized_items(self):
        self.mock_db.query.return_value = {"Items": [_DDB_ITEM]}
        result = self.repo.list_by_fridge("fridge_1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["fridgeId"], "fridge_1")

    def test_returns_empty_list_when_no_subscribers(self):
        self.mock_db.query.return_value = {"Items": []}
        self.assertEqual(self.repo.list_by_fridge("fridge_1"), [])