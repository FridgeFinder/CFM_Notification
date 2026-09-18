"""Unit tests for layers/python/auth_utils.py"""
import json
import unittest

from auth_utils import get_authenticated_user_id, validate_user_authorization

def _make_event(sub=None):
    """Build an API Gateway v2 event with optional JWT sub claim."""
    event = {"requestContext": {"authorizer": {"jwt": {"claims": {}}}}}
    if sub is not None:
        event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"] = sub
    return event


class TestGetAuthenticatedUserId(unittest.TestCase):
    def test_returns_sub_from_jwt_claims(self):
        self.assertEqual(get_authenticated_user_id(_make_event(sub="user_123")), "user_123")

    def test_returns_none_when_sub_absent(self):
        self.assertIsNone(get_authenticated_user_id(_make_event()))

    def test_returns_none_when_requestcontext_missing(self):
        self.assertIsNone(get_authenticated_user_id({}))

    def test_returns_none_when_authorizer_missing(self):
        self.assertIsNone(get_authenticated_user_id({"requestContext": {}}))

    def test_returns_none_when_jwt_missing(self):
        self.assertIsNone(
            get_authenticated_user_id({"requestContext": {"authorizer": {}}})
        )

    def test_returns_none_when_claims_missing(self):
        self.assertIsNone(
            get_authenticated_user_id(
                {"requestContext": {"authorizer": {"jwt": {}}}}
            )
        )


class TestValidateUserAuthorization(unittest.TestCase):
    def test_returns_none_when_valid(self):
        result = validate_user_authorization("user_1", "user_1", "req-1", "/path")
        self.assertIsNone(result)

    def test_returns_500_when_no_authenticated_user(self):
        result = validate_user_authorization(None, "user_1", "req-1", "/path")
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertIn("Authentication failed", body["error"]["message"])

    def test_returns_500_when_authenticated_user_is_empty_string(self):
        result = validate_user_authorization("", "user_1", "req-1", "/path")
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Authentication failed: No sub found in JWT")
        self.assertEqual(body["error"]["code"], "INTERNAL_SERVER_ERROR")

    def test_returns_500_when_authenticated_user_is_whitespace(self):
        result = validate_user_authorization("   ", "user_1", "req-1", "/path")
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Authentication failed: No sub found in JWT")
        self.assertEqual(body["error"]["code"], "INTERNAL_SERVER_ERROR")

    def test_returns_403_when_user_id_does_not_match_authenticated_user(self):
        result = validate_user_authorization("auth_user", "other_user", "req-1", "/path")
        self.assertEqual(result["statusCode"], 403)
        body = json.loads(result["body"])
        self.assertIn("Unauthorized", body["error"]["message"])

    def test_returns_none_with_optional_http_method(self):
        result = validate_user_authorization("u1", "u1", "req-1", "/path", "GET")
        self.assertIsNone(result)

    def test_returns_403_with_optional_http_method(self):
        result = validate_user_authorization("auth", "other", "req-1", "/path", "DELETE")
        self.assertEqual(result["statusCode"], 403)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Unauthorized: User can only access their own data")
        self.assertEqual(body["error"]["code"], "FORBIDDEN")