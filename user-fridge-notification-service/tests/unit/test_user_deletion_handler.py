"""Unit tests for functions/user_deletion_handler/user_deletion_handler.py"""
import unittest
from unittest.mock import patch
from botocore.exceptions import ClientError

import user_deletion_handler as handler

_ITEMS = [
    {"userId": {"S": "user_1"}, "fridgeId": {"S": "fridge_1"}},
    {"userId": {"S": "user_1"}, "fridgeId": {"S": "fridge_2"}},
]


class _FakeContext:
    aws_request_id = "req-test-123"


class TestUserDeletionHandler(unittest.TestCase):
    def _make_event(self, user_id="user_1"):
        return {"detail": {"userId": user_id}}

    def test_deletes_all_notifications_and_returns_summary(self):
        with patch.object(handler, "dynamodb") as mock_db:
            mock_db.query.return_value = {"Items": _ITEMS}
            mock_db.delete_item.return_value = {}
            result = handler.lambda_handler(self._make_event(), _FakeContext())

        self.assertEqual(result["userId"], "user_1")
        self.assertEqual(result["totalCount"], 2)
        self.assertEqual(result["deletedCount"], 2)
        self.assertEqual(result["failedCount"], 0)
        self.assertEqual(mock_db.delete_item.call_count, 2)

    def test_returns_zero_counts_when_user_has_no_notifications(self):
        with patch.object(handler, "dynamodb") as mock_db:
            mock_db.query.return_value = {"Items": []}
            result = handler.lambda_handler(self._make_event(), _FakeContext())

        self.assertEqual(result["totalCount"], 0)
        self.assertEqual(result["deletedCount"], 0)
        self.assertEqual(result["failedCount"], 0)
        mock_db.delete_item.assert_not_called()

    def test_partial_failure_raises_and_reports_counts(self):
        """If any delete fails, an exception is raised to trigger EventBridge retry."""
        with patch.object(handler, "dynamodb") as mock_db:
            mock_db.query.return_value = {"Items": _ITEMS}
            mock_db.delete_item.side_effect = [
                {},
                ClientError(
                    {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": ""}},
                    "DeleteItem",
                ),
            ]
            with self.assertRaises(Exception) as ctx:
                handler.lambda_handler(self._make_event(), _FakeContext())

        self.assertIn("1", str(ctx.exception))

    def test_raises_key_error_when_event_detail_missing(self):
        with self.assertRaises(KeyError):
            handler.lambda_handler({}, _FakeContext())

    def test_raises_key_error_when_user_id_missing_from_detail(self):
        with self.assertRaises(KeyError):
            handler.lambda_handler({"detail": {}}, _FakeContext())

    def test_queries_by_correct_user_id(self):
        with patch.object(handler, "dynamodb") as mock_db:
            mock_db.query.return_value = {"Items": []}
            handler.lambda_handler(self._make_event("specific_user"), _FakeContext())

        call_kwargs = mock_db.query.call_args[1]
        self.assertIn(":userId", call_kwargs["ExpressionAttributeValues"])
        self.assertEqual(
            call_kwargs["ExpressionAttributeValues"][":userId"]["S"], "specific_user"
        )

    def test_delete_uses_correct_keys(self):
        with patch.object(handler, "dynamodb") as mock_db:
            mock_db.query.return_value = {"Items": [_ITEMS[0]]}
            mock_db.delete_item.return_value = {}
            handler.lambda_handler(self._make_event(), _FakeContext())

        delete_call_kwargs = mock_db.delete_item.call_args[1]
        self.assertEqual(delete_call_kwargs["Key"]["userId"]["S"], "user_1")
        self.assertEqual(delete_call_kwargs["Key"]["fridgeId"]["S"], "fridge_1")


class TestDeleteNotification(unittest.TestCase):
    def test_calls_delete_item_with_correct_table_and_keys(self):
        with patch.object(handler, "dynamodb") as mock_db, \
             patch.object(handler, "table_name", "TestTable"):
            mock_db.delete_item.return_value = {}
            handler.delete_notification("user_1", "fridge_1")

        call_kwargs = mock_db.delete_item.call_args[1]
        self.assertEqual(call_kwargs["TableName"], "TestTable")
        self.assertEqual(call_kwargs["Key"]["userId"]["S"], "user_1")
        self.assertEqual(call_kwargs["Key"]["fridgeId"]["S"], "fridge_1")

    def test_propagates_client_error(self):
        with patch.object(handler, "dynamodb") as mock_db:
            mock_db.delete_item.side_effect = ClientError(
                {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": ""}},
                "DeleteItem",
            )
            with self.assertRaises(ClientError):
                handler.delete_notification("user_1", "fridge_1")


class TestQueryNotifications(unittest.TestCase):
    def test_returns_items_for_user(self):
        with patch.object(handler, "dynamodb") as mock_db, \
             patch.object(handler, "table_name", "TestTable"):
            mock_db.query.return_value = {"Items": _ITEMS}
            result = handler.query_notifications("user_1")

        self.assertEqual(result, _ITEMS)

    def test_returns_empty_list_when_no_items(self):
        with patch.object(handler, "dynamodb") as mock_db:
            mock_db.query.return_value = {"Items": []}
            result = handler.query_notifications("user_1")

        self.assertEqual(result, [])

    def test_queries_correct_table_and_user_id(self):
        with patch.object(handler, "dynamodb") as mock_db, \
             patch.object(handler, "table_name", "TestTable"):
            mock_db.query.return_value = {"Items": []}
            handler.query_notifications("specific_user")

        call_kwargs = mock_db.query.call_args[1]
        self.assertEqual(call_kwargs["TableName"], "TestTable")
        self.assertEqual(
            call_kwargs["ExpressionAttributeValues"][":userId"]["S"], "specific_user"
        )

    def test_propagates_client_error(self):
        with patch.object(handler, "dynamodb") as mock_db:
            mock_db.query.side_effect = ClientError(
                {"Error": {"Code": "InternalServerError", "Message": ""}}, "Query"
            )
            with self.assertRaises(ClientError):
                handler.query_notifications("user_1")