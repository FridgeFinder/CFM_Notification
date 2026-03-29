"""Unit tests for layers/python/response_utils.py"""
import json
import unittest

from response_utils import ErrorCode, HttpStatus, error_response, http_response


class TestHttpStatus(unittest.TestCase):
    def test_status_code_values(self):
        self.assertEqual(HttpStatus.OK, 200)
        self.assertEqual(HttpStatus.CREATED, 201)
        self.assertEqual(HttpStatus.NO_CONTENT, 204)
        self.assertEqual(HttpStatus.BAD_REQUEST, 400)
        self.assertEqual(HttpStatus.UNAUTHORIZED, 401)
        self.assertEqual(HttpStatus.FORBIDDEN, 403)
        self.assertEqual(HttpStatus.NOT_FOUND, 404)
        self.assertEqual(HttpStatus.CONFLICT, 409)
        self.assertEqual(HttpStatus.INTERNAL_SERVER_ERROR, 500)


class TestErrorCode(unittest.TestCase):
    def test_error_code_values(self):
        self.assertEqual(ErrorCode.ITEM_NOT_FOUND.value, "ITEM_NOT_FOUND")
        self.assertEqual(ErrorCode.ITEM_ALREADY_EXISTS.value, "ITEM_ALREADY_EXISTS")
        self.assertEqual(ErrorCode.FORBIDDEN.value, "FORBIDDEN")
        self.assertEqual(ErrorCode.VALIDATION_ERROR.value, "VALIDATION_ERROR")
        self.assertEqual(ErrorCode.INTERNAL_SERVER_ERROR.value, "INTERNAL_SERVER_ERROR")
        self.assertEqual(ErrorCode.MISSING_REQUIRED_FIELD.value, "MISSING_REQUIRED_FIELD")
        self.assertEqual(ErrorCode.UNAUTHORIZED.value, "UNAUTHORIZED")


class TestHttpResponse(unittest.TestCase):
    def test_returns_correct_status_code(self):
        response = http_response(200, {"key": "value"})
        self.assertEqual(response["statusCode"], 200)

    def test_includes_cors_header(self):
        response = http_response(200, {})
        self.assertEqual(response["headers"]["Access-Control-Allow-Origin"], "*")

    def test_includes_content_type_header(self):
        response = http_response(200, {})
        self.assertEqual(response["headers"]["Content-Type"], "application/json")

    def test_body_is_json_serialized(self):
        response = http_response(200, {"count": 3, "items": ["a", "b"]})
        self.assertIsInstance(response["body"], str)
        body = json.loads(response["body"])
        self.assertEqual(body["count"], 3)
        self.assertEqual(body["items"], ["a", "b"])

    def test_request_id_added_to_headers_when_provided(self):
        response = http_response(200, {}, request_id="req-abc-123")
        self.assertEqual(response["headers"]["X-Request-ID"], "req-abc-123")

    def test_no_request_id_header_when_omitted(self):
        response = http_response(200, {})
        self.assertNotIn("X-Request-ID", response["headers"])

    def test_none_data_serialized_as_null(self):
        response = http_response(204, None)
        self.assertEqual(response["statusCode"], 204)
        self.assertIsNone(json.loads(response["body"]))

    def test_created_status(self):
        response = http_response(HttpStatus.CREATED, {"id": "123"})
        self.assertEqual(response["statusCode"], 201)


class TestErrorResponse(unittest.TestCase):
    def test_returns_error_structure(self):
        response = error_response(404, "Item not found", ErrorCode.ITEM_NOT_FOUND)
        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["message"], "Item not found")
        self.assertEqual(body["error"]["code"], "ITEM_NOT_FOUND")

    def test_error_code_stored_as_string_value(self):
        response = error_response(403, "Forbidden", ErrorCode.FORBIDDEN)
        body = json.loads(response["body"])
        self.assertIsInstance(body["error"]["code"], str)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")

    def test_request_id_forwarded_to_headers(self):
        response = error_response(
            400, "Bad input", ErrorCode.VALIDATION_ERROR, request_id="req-xyz"
        )
        self.assertEqual(response["headers"]["X-Request-ID"], "req-xyz")

    def test_no_request_id_when_omitted(self):
        response = error_response(500, "Server error", ErrorCode.INTERNAL_SERVER_ERROR)
        self.assertNotIn("X-Request-ID", response["headers"])

    def test_cors_header_present(self):
        response = error_response(404, "Not found", ErrorCode.ITEM_NOT_FOUND)
        self.assertEqual(response["headers"]["Access-Control-Allow-Origin"], "*")