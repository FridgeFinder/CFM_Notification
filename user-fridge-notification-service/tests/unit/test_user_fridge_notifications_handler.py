"""Unit tests for functions/fridge_notifications/user/user_fridge_notifications_handler.py"""
import json
import unittest
from unittest.mock import patch

import user_fridge_notifications_handler as handler

_ALL_PREFS = {
    "good": True,
    "dirty": True,
    "outOfOrder": True,
    "notAtLocation": True,
    "ghost": True,
    "noFood": True,
    "hasFood": True,
}

_ITEM_DICT = {
    "userId": "user_1",
    "fridgeId": "fridge_1",
    "contactTypePreferences": {"email": _ALL_PREFS},
}


class _FakeContext:
    aws_request_id = "req-test-123"


def _make_event(method="GET", user_id="user_1", fridge_id="fridge_1", sub="user_1", body=None):
    return {
        "requestContext": {
            "http": {"method": method},
            "authorizer": {"jwt": {"claims": {"sub": sub}}},
        },
        "pathParameters": {"user_id": user_id, "fridge_id": fridge_id},
        "rawPath": f"/v1/users/{user_id}/notifications/{fridge_id}",
        "body": json.dumps(body) if body else None,
    }


class TestValidateRequestParameters(unittest.TestCase):
    def test_returns_none_when_all_params_valid(self):
        result = handler.validate_request_parameters(
            "user_1", "user_1", "fridge_1", "req-1", "/path", "GET"
        )
        self.assertIsNone(result)

    def test_returns_400_when_fridge_id_missing(self):
        result = handler.validate_request_parameters(
            "user_1", "user_1", None, "req-1", "/path", "GET"
        )
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Missing required path parameter: fridge_id")
        self.assertEqual(body["error"]["code"], "MISSING_REQUIRED_FIELD")

    def test_returns_400_when_fridge_id_whitespace(self):
        result = handler.validate_request_parameters(
            "user_1", "user_1", "   ", "req-1", "/path", "GET"
        )
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Missing required path parameter: fridge_id")
        self.assertEqual(body["error"]["code"], "MISSING_REQUIRED_FIELD")

    def test_returns_400_when_user_id_missing(self):
        result = handler.validate_request_parameters(
            "user_1", None, "fridge_1", "req-1", "/path", "GET"
        )
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Missing required path parameter: user_id")
        self.assertEqual(body["error"]["code"], "MISSING_REQUIRED_FIELD")

    def test_returns_403_when_user_id_mismatch(self):
        result = handler.validate_request_parameters(
            "auth_user", "other_user", "fridge_1", "req-1", "/path", "GET"
        )
        self.assertEqual(result["statusCode"], 403)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Unauthorized: User can only access their own data")
        self.assertEqual(body["error"]["code"], "FORBIDDEN")


class TestHandleGetRequest(unittest.TestCase):
    def test_delegates_to_service(self):
        with patch.object(handler, "service") as mock_svc:
            mock_svc.get_user_fridge_notification.return_value = {"statusCode": 200, "body": "{}"}
            handler.handle_get_request("user_1", "fridge_1", "req-1")
        mock_svc.get_user_fridge_notification.assert_called_once_with(
            userId="user_1", fridgeId="fridge_1", request_id="req-1"
        )


class TestHandlePostRequest(unittest.TestCase):
    def _post_event(self, body):
        return {"body": json.dumps(body) if body is not None else None}

    def test_returns_400_when_body_missing(self):
        result = handler.handle_post_request({"body": None}, "user_1", "fridge_1", "req-1")
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Missing request body")
        self.assertEqual(body["error"]["code"], "MISSING_BODY")

    def test_returns_400_when_body_is_invalid_json(self):
        result = handler.handle_post_request({"body": "not-json"}, "user_1", "fridge_1", "req-1")
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Invalid JSON in request body")
        self.assertEqual(body["error"]["code"], "INVALID_JSON")

    def test_returns_400_when_model_validation_fails(self):
        result = handler.handle_post_request(
            {"body": json.dumps({"contactTypePreferences": {"bad_key": {}}})},
            "user_1",
            "fridge_1",
            "req-1",
        )
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")

    def test_delegates_to_service_on_valid_body(self):
        body = {"contactTypePreferences": {"email": _ALL_PREFS}}
        with patch.object(handler, "service") as mock_svc:
            mock_svc.post_user_fridge_notification.return_value = {"statusCode": 201, "body": "{}"}
            handler.handle_post_request(
                {"body": json.dumps(body)}, "user_1", "fridge_1", "req-1"
            )
        mock_svc.post_user_fridge_notification.assert_called_once()


class TestHandlePatchRequest(unittest.TestCase):
    def test_returns_400_when_body_missing(self):
        result = handler.handle_patch_request({"body": None}, "user_1", "fridge_1", "req-1")
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Missing request body")
        self.assertEqual(body["error"]["code"], "MISSING_BODY")

    def test_returns_400_when_body_is_invalid_json(self):
        result = handler.handle_patch_request({"body": "not-json"}, "user_1", "fridge_1", "req-1")
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "Invalid JSON in request body")
        self.assertEqual(body["error"]["code"], "INVALID_JSON")

    def test_returns_400_when_contacttypepreferences_missing(self):
        result = handler.handle_patch_request(
            {"body": json.dumps({})}, "user_1", "fridge_1", "req-1"
        )
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"]["message"], "contactTypePreferences is required")
        self.assertEqual(body["error"]["code"], "MISSING_REQUIRED_FIELD")

    def test_delegates_to_service_on_valid_body(self):
        body = {"contactTypePreferences": {"email": _ALL_PREFS}}
        with patch.object(handler, "service") as mock_svc:
            mock_svc.patch_user_fridge_notification.return_value = {"statusCode": 200, "body": "{}"}
            handler.handle_patch_request(
                {"body": json.dumps(body)}, "user_1", "fridge_1", "req-1"
            )
        mock_svc.patch_user_fridge_notification.assert_called_once_with(
            userId="user_1",
            fridgeId="fridge_1",
            contactTypePreferences={"email": _ALL_PREFS},
            request_id="req-1",
        )


class TestHandleDeleteRequest(unittest.TestCase):
    def test_delegates_to_service(self):
        with patch.object(handler, "service") as mock_svc:
            mock_svc.delete_user_fridge_notification.return_value = {"statusCode": 204, "body": "null"}
            handler.handle_delete_request("user_1", "fridge_1", "req-1")
        mock_svc.delete_user_fridge_notification.assert_called_once_with(
            userId="user_1", fridgeId="fridge_1", request_id="req-1"
        )


class TestLambdaHandlerRouting(unittest.TestCase):
    def test_routes_get_to_get_handler(self):
        with patch.object(handler, "service") as mock_svc:
            mock_svc.get_user_fridge_notification.return_value = {"statusCode": 200, "body": json.dumps(_ITEM_DICT)}
            response = handler.lambda_handler(_make_event("GET"), _FakeContext())
        self.assertEqual(response["statusCode"], 200)
        mock_svc.get_user_fridge_notification.assert_called_once()

    def test_routes_post_to_post_handler(self):
        body = {"contactTypePreferences": {"email": _ALL_PREFS}}
        with patch.object(handler, "service") as mock_svc:
            mock_svc.post_user_fridge_notification.return_value = {"statusCode": 201, "body": json.dumps(_ITEM_DICT)}
            response = handler.lambda_handler(_make_event("POST", body=body), _FakeContext())
        self.assertEqual(response["statusCode"], 201)
        mock_svc.post_user_fridge_notification.assert_called_once()

    def test_routes_patch_to_patch_handler(self):
        body = {"contactTypePreferences": {"email": _ALL_PREFS}}
        with patch.object(handler, "service") as mock_svc:
            mock_svc.patch_user_fridge_notification.return_value = {"statusCode": 200, "body": json.dumps(_ITEM_DICT)}
            response = handler.lambda_handler(_make_event("PATCH", body=body), _FakeContext())
        self.assertEqual(response["statusCode"], 200)
        mock_svc.patch_user_fridge_notification.assert_called_once()

    def test_routes_delete_to_delete_handler(self):
        with patch.object(handler, "service") as mock_svc:
            mock_svc.delete_user_fridge_notification.return_value = {"statusCode": 204, "body": "null"}
            response = handler.lambda_handler(_make_event("DELETE"), _FakeContext())
        self.assertEqual(response["statusCode"], 204)
        mock_svc.delete_user_fridge_notification.assert_called_once()

    def test_returns_500_for_unknown_http_method(self):
        response = handler.lambda_handler(_make_event("OPTIONS"), _FakeContext())
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "Invalid HTTP method")
        self.assertEqual(body["error"]["code"], "INTERNAL_SERVER_ERROR")

    def test_returns_403_when_user_id_mismatch(self):
        response = handler.lambda_handler(
            _make_event("GET", user_id="user_1", sub="user_2"), _FakeContext()
        )
        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "Unauthorized: User can only access their own data")
        self.assertEqual(body["error"]["code"], "FORBIDDEN")

    def test_returns_400_when_fridge_id_missing(self):
        event = _make_event("GET")
        event["pathParameters"] = {"user_id": "user_1"}
        response = handler.lambda_handler(event, _FakeContext())
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "Missing required path parameter: fridge_id")
        self.assertEqual(body["error"]["code"], "MISSING_REQUIRED_FIELD")

    def test_returns_400_when_user_id_missing(self):
        event = _make_event("GET")
        event["pathParameters"] = {"fridge_id": "fridge_1"}
        response = handler.lambda_handler(event, _FakeContext())
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "Missing required path parameter: user_id")
        self.assertEqual(body["error"]["code"], "MISSING_REQUIRED_FIELD")

    def test_returns_500_on_unhandled_service_exception(self):
        with patch.object(handler, "service") as mock_svc:
            mock_svc.get_user_fridge_notification.side_effect = Exception("unexpected")
            response = handler.lambda_handler(_make_event("GET"), _FakeContext())
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "Internal server error")
        self.assertEqual(body["error"]["code"], "INTERNAL_SERVER_ERROR")