"""Unit tests for layers/python/dynamodb_utils.py"""
import os
import unittest
from unittest.mock import patch

from dynamodb_utils import dict_to_dynamodb, dynamodb_to_dict, get_ddb_connection


class TestGetDdbConnection(unittest.TestCase):
    @patch("dynamodb_utils.boto3")
    def test_uses_localstack_endpoint_when_local(self, mock_boto3):
        with patch.dict(os.environ, {"DEPLOYMENT_TARGET": "local"}):
            get_ddb_connection()
        mock_boto3.client.assert_called_once_with(
            "dynamodb", endpoint_url="http://localstack:4566/"
        )

    @patch("dynamodb_utils.boto3")
    def test_uses_aws_client_when_deployment_target_is_aws(self, mock_boto3):
        with patch.dict(os.environ, {"DEPLOYMENT_TARGET": "aws"}):
            get_ddb_connection()
        mock_boto3.client.assert_called_once_with("dynamodb")

    @patch("dynamodb_utils.boto3")
    def test_defaults_to_localstack_when_env_var_missing(self, mock_boto3):
        env = {k: v for k, v in os.environ.items() if k != "DEPLOYMENT_TARGET"}
        with patch.dict(os.environ, env, clear=True):
            get_ddb_connection()
        _, kwargs = mock_boto3.client.call_args
        self.assertIn("endpoint_url", kwargs)


class TestDictToDynamodb(unittest.TestCase):
    def test_serializes_string(self):
        result = dict_to_dynamodb({"userId": "user_1"})
        self.assertEqual(result, {"userId": {"S": "user_1"}})

    def test_serializes_boolean(self):
        result = dict_to_dynamodb({"active": True})
        self.assertEqual(result, {"active": {"BOOL": True}})

    def test_serializes_number_as_n_type(self):
        result = dict_to_dynamodb({"count": 42})
        self.assertIn("N", result["count"])

    def test_serializes_nested_dict_as_map(self):
        result = dict_to_dynamodb({"prefs": {"good": True}})
        self.assertIn("M", result["prefs"])
        self.assertIn("good", result["prefs"]["M"])

    def test_serializes_none_as_null(self):
        result = dict_to_dynamodb({"field": None})
        self.assertEqual(result, {"field": {"NULL": True}})

    def test_empty_dict_returns_empty(self):
        self.assertEqual(dict_to_dynamodb({}), {})

    def test_multiple_fields(self):
        result = dict_to_dynamodb({"a": "x", "b": True})
        self.assertIn("a", result)
        self.assertIn("b", result)


class TestDynamodbToDict(unittest.TestCase):
    def test_deserializes_string(self):
        result = dynamodb_to_dict({"userId": {"S": "user_1"}})
        self.assertEqual(result, {"userId": "user_1"})

    def test_deserializes_boolean(self):
        result = dynamodb_to_dict({"active": {"BOOL": True}})
        self.assertEqual(result, {"active": True})

    def test_deserializes_number(self):
        result = dynamodb_to_dict({"count": {"N": "42"}})
        from decimal import Decimal
        self.assertEqual(result["count"], Decimal("42"))

    def test_deserializes_null(self):
        result = dynamodb_to_dict({"field": {"NULL": True}})
        self.assertIsNone(result["field"])

    def test_empty_item_returns_empty(self):
        self.assertEqual(dynamodb_to_dict({}), {})

    def test_roundtrip_preserves_string_and_bool(self):
        original = {"userId": "u1", "fridgeId": "f1"}
        self.assertEqual(dynamodb_to_dict(dict_to_dynamodb(original)), original)

    def test_roundtrip_preserves_nested_dict(self):
        original = {"prefs": {"good": True, "dirty": False}}
        result = dynamodb_to_dict(dict_to_dynamodb(original))
        self.assertEqual(result["prefs"]["good"], True)
        self.assertEqual(result["prefs"]["dirty"], False)