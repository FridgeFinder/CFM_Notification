"""Unit tests for functions/fridge_report_stream_processor/fridge_report_stream_processor_handler.py"""
import unittest
from unittest.mock import patch

import fridge_report_stream_processor_handler as handler


def _make_record(
    event_name="INSERT",
    fridge_id="fridge_1",
    condition="good",
    food_level="2",
):
    """Build a minimal DynamoDB Stream record."""
    return {
        "eventName": event_name,
        "dynamodb": {
            "NewImage": {
                "fridgeId": {"S": fridge_id},
                "condition": {"S": condition},
                "foodPercentage": {"N": food_level},
            }
        },
    }


_ALL_PREFS = {
    "good": True,
    "dirty": True,
    "outOfOrder": True,
    "notAtLocation": True,
    "ghost": True,
    "noFood": True,
    "hasFood": True,
}


class TestLambdaHandlerRecordFiltering(unittest.TestCase):
    def test_processes_insert_records_and_returns_count(self):
        with patch.object(handler, "query_notifications_by_fridge", return_value=[]):
            result = handler.lambda_handler({"Records": [_make_record()]}, None)
        self.assertEqual(result["records_processed"], 1)

    def test_skips_modify_events(self):
        with patch.object(handler, "query_notifications_by_fridge") as mock_q:
            result = handler.lambda_handler(
                {"Records": [_make_record(event_name="MODIFY")]}, None
            )
        self.assertEqual(result["records_processed"], 0)
        mock_q.assert_not_called()

    def test_skips_remove_events(self):
        with patch.object(handler, "query_notifications_by_fridge") as mock_q:
            result = handler.lambda_handler(
                {"Records": [_make_record(event_name="REMOVE")]}, None
            )
        self.assertEqual(result["records_processed"], 0)
        mock_q.assert_not_called()

    def test_skips_records_missing_fridge_id(self):
        record = {
            "eventName": "INSERT",
            "dynamodb": {
                "NewImage": {
                    "condition": {"S": "good"},
                    "foodPercentage": {"N": "2"},
                }
            },
        }
        result = handler.lambda_handler({"Records": [record]}, None)
        self.assertEqual(result["records_processed"], 0)

    def test_skips_records_missing_condition(self):
        record = {
            "eventName": "INSERT",
            "dynamodb": {
                "NewImage": {
                    "fridgeId": {"S": "fridge_1"},
                    "foodPercentage": {"N": "2"},
                }
            },
        }
        result = handler.lambda_handler({"Records": [record]}, None)
        self.assertEqual(result["records_processed"], 0)

    def test_skips_records_with_no_new_image(self):
        record = {"eventName": "INSERT", "dynamodb": {}}
        result = handler.lambda_handler({"Records": [record]}, None)
        self.assertEqual(result["records_processed"], 0)

    def test_empty_records_list_returns_zero(self):
        result = handler.lambda_handler({"Records": []}, None)
        self.assertEqual(result["records_processed"], 0)

    def test_exception_in_one_record_does_not_stop_others(self):
        records = [_make_record(fridge_id="f1"), _make_record(fridge_id="f2")]
        with patch.object(
            handler,
            "query_notifications_by_fridge",
            side_effect=[Exception("db failure"), []],
        ):
            result = handler.lambda_handler({"Records": records}, None)
        # First record caused exception (not counted); second succeeded.
        self.assertEqual(result["records_processed"], 1)

    def test_returns_message_and_records_processed_keys(self):
        with patch.object(handler, "query_notifications_by_fridge", return_value=[]):
            result = handler.lambda_handler({"Records": [_make_record()]}, None)
        self.assertIn("message", result)
        self.assertIn("records_processed", result)


class TestLambdaHandlerConditionAndFoodLevelMapping(unittest.TestCase):
    def test_unknown_condition_still_counts_record_as_processed(self):
        """process_fridge_report returns early but the record is still counted."""
        with patch.object(handler, "query_notifications_by_fridge", return_value=[]):
            result = handler.lambda_handler(
                {"Records": [_make_record(condition="unknown_condition")]}, None
            )
        self.assertEqual(result["records_processed"], 1)

    def test_unmapped_food_level_still_counts_record_as_processed(self):
        with patch.object(handler, "query_notifications_by_fridge", return_value=[]):
            result = handler.lambda_handler(
                {"Records": [_make_record(food_level="99")]}, None
            )
        self.assertEqual(result["records_processed"], 1)


class TestProcessFridgeReport(unittest.TestCase):
    def _pref_with_email(self, prefs=None):
        return {
            "userId": "user_1",
            "contactTypePreferences": {"email": prefs or _ALL_PREFS},
        }

    def _pref_with_device(self, prefs=None):
        return {
            "userId": "user_1",
            "contactTypePreferences": {"device": prefs or _ALL_PREFS},
        }

    def _user(self, email=True, push=False):
        u = {"settings": {
            "emailNotificationEnabled": email,
            "pushNotificationEnabled": push,
        }}
        if email:
            u["email"] = "user@example.com"
        if push:
            u["fcmToken"] = "fcm_token_abc"
        return u

    def test_sends_email_notification_when_email_enabled(self):
        with patch.object(handler, "query_notifications_by_fridge", return_value=[self._pref_with_email()]), \
             patch.object(handler, "get_user_details", return_value=self._user(email=True)), \
             patch.object(handler, "send_email_notification") as mock_email:
            handler.process_fridge_report("fridge_1", "good", 1)
        mock_email.assert_called_once()

    def test_sends_push_notification_when_push_enabled(self):
        with patch.object(handler, "query_notifications_by_fridge", return_value=[self._pref_with_device()]), \
             patch.object(handler, "get_user_details", return_value=self._user(push=True)), \
             patch.object(handler, "send_push_notification") as mock_push:
            handler.process_fridge_report("fridge_1", "good", 1)
        mock_push.assert_called_once()

    def test_skips_notification_when_user_details_not_found(self):
        with patch.object(handler, "query_notifications_by_fridge", return_value=[self._pref_with_email()]), \
             patch.object(handler, "get_user_details", return_value=None), \
             patch.object(handler, "send_email_notification") as mock_email:
            handler.process_fridge_report("fridge_1", "good", 1)
        mock_email.assert_not_called()

    def test_no_email_sent_when_email_notifications_disabled(self):
        user = {"email": "user@example.com", "settings": {"emailNotificationEnabled": False, "pushNotificationEnabled": False}}
        with patch.object(handler, "query_notifications_by_fridge", return_value=[self._pref_with_email()]), \
             patch.object(handler, "get_user_details", return_value=user), \
             patch.object(handler, "send_email_notification") as mock_email:
            handler.process_fridge_report("fridge_1", "good", 1)
        mock_email.assert_not_called()

    def test_no_push_sent_when_no_fcm_token(self):
        user = {"settings": {"emailNotificationEnabled": False, "pushNotificationEnabled": True}}
        # fcmToken absent
        with patch.object(handler, "query_notifications_by_fridge", return_value=[self._pref_with_device()]), \
             patch.object(handler, "get_user_details", return_value=user), \
             patch.object(handler, "send_push_notification") as mock_push:
            handler.process_fridge_report("fridge_1", "good", 1)
        mock_push.assert_not_called()

    def test_returns_early_for_unknown_condition(self):
        with patch.object(handler, "query_notifications_by_fridge", return_value=[self._pref_with_email()]), \
             patch.object(handler, "send_email_notification") as mock_email:
            handler.process_fridge_report("fridge_1", "unknown_condition", 1)
        # Notifications never dispatched regardless of subscriptions
        mock_email.assert_not_called()