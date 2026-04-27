"""Unit tests for functions/fridge_report_stream_processor/services/notification_service.py"""
import unittest
from unittest.mock import MagicMock, patch

from services import notification_service

_ALL_TRUE_PREFS = {
    "good": True,
    "dirty": True,
    "outOfOrder": True,
    "notAtLocation": True,
    "ghost": True,
    "noFood": True,
    "hasFood": True,
}

class TestGetNotificationMessage(unittest.TestCase):
    def test_returns_combined_message_when_both_prefs_match(self):
        prefs = {"good": True, "hasFood": True}
        result = notification_service.get_notification_message(
            prefs, "good", "hasFood", 2
        )
        self.assertIn("Fridge is in good condition", result)
        self.assertIn("Fridge has plenty of food", result)

    def test_returns_condition_message_only_when_food_pref_false(self):
        prefs = {"good": True, "hasFood": False}
        result = notification_service.get_notification_message(
            prefs, "good", "hasFood", 2
        )
        self.assertEqual(result, "Fridge is in good condition")

    def test_returns_food_message_only_when_condition_pref_false(self):
        prefs = {"good": False, "noFood": True}
        result = notification_service.get_notification_message(
            prefs, "good", "noFood", 0
        )
        self.assertEqual(result, "Fridge is out of food")

    def test_returns_none_when_no_pref_matches(self):
        prefs = {"good": False, "hasFood": False}
        result = notification_service.get_notification_message(
            prefs, "good", "hasFood", 2
        )
        self.assertIsNone(result)

    def test_returns_none_for_empty_prefs(self):
        result = notification_service.get_notification_message(
            {}, "good", "hasFood", 2
        )
        self.assertIsNone(result)

    def test_dirty_condition_message(self):
        prefs = {"dirty": True, "noFood": False}
        result = notification_service.get_notification_message(
            prefs, "dirty", "noFood", 0
        )
        self.assertEqual(result, "Fridge needs cleaning")

    def test_out_of_order_condition_message(self):
        prefs = {"outOfOrder": True, "hasFood": False}
        result = notification_service.get_notification_message(
            prefs, "outOfOrder", "hasFood", 3
        )
        self.assertEqual(result, "Fridge needs repairs")


class TestSendEmailNotification(unittest.TestCase):
    def _call_with_mock_ses(self, prefs, condition="good", food_condition="hasFood", food_level=1):
        with patch.object(notification_service, "ses") as mock_ses:
            notification_service.send_email_notification(
                prefs,
                "user@example.com",
                "fridge_1",
                condition,
                food_condition,
                food_level,
            )
            return mock_ses

    def test_sends_email_when_prefs_match(self):
        mock_ses = self._call_with_mock_ses({"good": True, "hasFood": True})
        mock_ses.send_email.assert_called_once()

    def test_does_not_send_when_no_prefs_match(self):
        mock_ses = self._call_with_mock_ses({"good": False, "hasFood": False})
        mock_ses.send_email.assert_not_called()

    def test_email_sent_to_correct_address(self):
        mock_ses = self._call_with_mock_ses({"good": True, "hasFood": True})
        call_kwargs = mock_ses.send_email.call_args[1]
        self.assertIn("user@example.com", call_kwargs["Destination"]["ToAddresses"])

    def test_email_subject_contains_fridge_id(self):
        mock_ses = self._call_with_mock_ses({"good": True, "hasFood": True})
        call_kwargs = mock_ses.send_email.call_args[1]
        self.assertIn("fridge_1", call_kwargs["Message"]["Subject"]["Data"])

    def test_does_not_raise_on_ses_exception(self):
        with patch.object(notification_service, "ses") as mock_ses:
            mock_ses.send_email.side_effect = Exception("SES timeout")
            # Should swallow the exception and log it
            notification_service.send_email_notification(
                {"good": True, "hasFood": True},
                "user@example.com",
                "fridge_1",
                "good",
                "hasFood",
                1,
            )


class TestSendPushNotification(unittest.TestCase):
    def _prefs(self, condition_on=True, food_on=True):
        return {"good": condition_on, "hasFood": food_on}

    def test_skips_when_firebase_not_initialized(self):
        with patch.object(notification_service.firebase_admin, "_apps", {}), \
             patch.object(notification_service, "messaging") as mock_msg:
            notification_service.send_push_notification(
                self._prefs(), "token_abc", "fridge_1", "good", "hasFood", 1
            )
        mock_msg.send.assert_not_called()

    def test_sends_push_when_firebase_initialized_and_pref_matches(self):
        fake_apps = {"default": MagicMock()}
        with patch.object(notification_service.firebase_admin, "_apps", fake_apps), \
             patch.object(notification_service, "messaging") as mock_msg:
            mock_msg.Message.return_value = MagicMock()
            notification_service.send_push_notification(
                self._prefs(), "token_abc", "fridge_1", "good", "hasFood", 1
            )
        mock_msg.send.assert_called_once()

    def test_does_not_send_when_no_pref_matches(self):
        fake_apps = {"default": MagicMock()}
        with patch.object(notification_service.firebase_admin, "_apps", fake_apps), \
             patch.object(notification_service, "messaging") as mock_msg:
            notification_service.send_push_notification(
                self._prefs(condition_on=False, food_on=False),
                "token_abc",
                "fridge_1",
                "good",
                "hasFood",
                1,
            )
        mock_msg.send.assert_not_called()

    def test_does_not_raise_on_generic_fcm_exception(self):
        fake_apps = {"default": MagicMock()}
        with patch.object(notification_service.firebase_admin, "_apps", fake_apps), \
             patch.object(notification_service, "messaging") as mock_msg:
            mock_msg.Message.return_value = MagicMock()
            mock_msg.send.side_effect = Exception("FCM error")
            mock_msg.UnregisteredError = type("UnregisteredError", (Exception,), {})
            mock_msg.SenderIdMismatchError = type("SenderIdMismatchError", (Exception,), {})
            # Should not raise
            notification_service.send_push_notification(
                self._prefs(), "token_abc", "fridge_1", "good", "hasFood", 1
            )