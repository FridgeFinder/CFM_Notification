"""Unit tests for functions/fridge_notifications/getAllUserNotifications/get_all_user_notifications_handler.py"""
import json
import unittest
from unittest.mock import patch

import get_all_user_notifications_handler as handler

# Minimal DynamoDB wire-format item used by mocked query results.
_DDB_ITEM = {
    "userId": {"S": "user_1"},
    "fridgeId": {"S": "fridge_1"},
}


class _FakeContext:
    aws_request_id = "req-test-123"


class TestValidateInput(unittest.TestCase):
    def test_none_user_id_returns_400(self):
        result = handler.validate_input(None, "auth_user", "req-1", "/path")
        self.assertIsNotNone(result)
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Missing required path parameter: user_id")
        self.assertEqual(body["error"]["code"], "MISSING_REQUIRED_FIELD")

    def test_empty_user_id_returns_400(self):
        result = handler.validate_input("", "auth_user", "req-1", "/path")
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Missing required path parameter: user_id")
        self.assertEqual(body["error"]["code"], "MISSING_REQUIRED_FIELD")

    def test_whitespace_only_user_id_returns_400(self):
        result = handler.validate_input("   ", "auth_user", "req-1", "/path")
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Missing required path parameter: user_id")
        self.assertEqual(body["error"]["code"], "MISSING_REQUIRED_FIELD")

    def test_user_id_mismatch_returns_403(self):
        result = handler.validate_input("user_1", "user_2", "req-1", "/path")
        self.assertEqual(result["statusCode"], 403)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Unauthorized: User can only access their own data")
        self.assertEqual(body["error"]["code"], "FORBIDDEN")

    def test_valid_params_returns_none(self):
        result = handler.validate_input("user_1", "user_1", "req-1", "/path")
        self.assertIsNone(result)


class TestListByUser(unittest.TestCase):
    def test_returns_deserialized_items(self):
        with patch.object(handler, "db_client") as mock_db:
            mock_db.query.return_value = {"Items": [_DDB_ITEM]}
            result = handler.list_by_user("user_1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["userId"], "user_1")

    def test_returns_empty_list_when_no_items(self):
        with patch.object(handler, "db_client") as mock_db:
            mock_db.query.return_value = {"Items": []}
            result = handler.list_by_user("user_1")
        self.assertEqual(result, [])


class TestLambdaHandler(unittest.TestCase):
    def _make_event(self, user_id="user_1", authenticated_sub="user_1"):
        return {
            "pathParameters": {"user_id": user_id},
            "rawPath": f"/v1/users/{user_id}/fridge-notifications",
            "requestContext": {
                "authorizer": {"jwt": {"claims": {"sub": authenticated_sub}}}
            },
        }

    def test_returns_200_with_notifications_list(self):
        with patch.object(handler, "db_client") as mock_db:
            mock_db.query.return_value = {"Items": [_DDB_ITEM]}
            response = handler.lambda_handler(self._make_event(), _FakeContext())

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["count"], 1)
        self.assertEqual(len(body["notifications"]), 1)
        self.assertEqual(body["notifications"][0]["userId"], "user_1")

    def test_returns_200_with_empty_list_when_no_notifications(self):
        with patch.object(handler, "db_client") as mock_db:
            mock_db.query.return_value = {"Items": []}
            response = handler.lambda_handler(self._make_event(), _FakeContext())

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["notifications"], [])

    def test_returns_400_when_user_id_missing(self):
        event = self._make_event()
        event["pathParameters"] = {}
        response = handler.lambda_handler(event, _FakeContext())
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "Missing required path parameter: user_id")
        self.assertEqual(body["error"]["code"], "MISSING_REQUIRED_FIELD")

    def test_returns_403_when_user_id_does_not_match_jwt(self):
        response = handler.lambda_handler(
            self._make_event(user_id="user_1", authenticated_sub="user_2"),
            _FakeContext(),
        )
        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "Unauthorized: User can only access their own data")
        self.assertEqual(body["error"]["code"], "FORBIDDEN")

    def test_returns_500_when_db_raises(self):
        with patch.object(handler, "db_client") as mock_db:
            mock_db.query.side_effect = Exception("unexpected DB error")
            response = handler.lambda_handler(self._make_event(), _FakeContext())
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "Internal server error")
        self.assertEqual(body["error"]["code"], "INTERNAL_SERVER_ERROR")

    def test_returns_500_when_jwt_sub_missing(self):
        """Missing sub in JWT claims means no authenticated_user_id -> 500."""
        event = {
            "pathParameters": {"user_id": "user_1"},
            "rawPath": "/v1/users/user_1/fridge-notifications",
            "requestContext": {"authorizer": {"jwt": {"claims": {}}}},
        }
        response = handler.lambda_handler(event, _FakeContext())
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "Authentication failed: No sub found in JWT")
        self.assertEqual(body["error"]["code"], "INTERNAL_SERVER_ERROR")

    def test_count_matches_notification_list_length(self):
        ddb_items = [
            {"userId": {"S": "user_1"}, "fridgeId": {"S": f"fridge_{i}"}}
            for i in range(3)
        ]
        with patch.object(handler, "db_client") as mock_db:
            mock_db.query.return_value = {"Items": ddb_items}
            response = handler.lambda_handler(self._make_event(), _FakeContext())

        body = json.loads(response["body"])
        self.assertEqual(body["count"], len(body["notifications"]))