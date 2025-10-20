import unittest
from datetime import datetime
from unittest.mock import patch
from Notification.dependencies.python.user_fridge_notifications_model import (
    UserFridgeNotificationModel,
    ContactInfoModel,
    ContactTypeStatusModel,
    ContactTypePreferencesModel,
    FridgePreferencesModel,
    validate_phone_number,
)

class TestUserFridgeNotificationModel(unittest.TestCase):
    def setUp(self):
        # reusable valid fridge preferences
        self.fridge_prefs = FridgePreferencesModel(
            good=True,
            dirty=True,
            out_of_order=True,
            not_at_location=True,
            ghost=True,
            food_level_0=True,
            food_level_1=True,
            food_level_2=True,
            food_level_3=True,
            cleaned=True,
        )

    def test_model_happy_path(self):
        contact_info = ContactInfoModel(email="test@example.com", sms="+14155552671")
        contact_types_status = ContactTypeStatusModel(sms="start", email="start")
        contact_types_preferences = ContactTypePreferencesModel(sms=self.fridge_prefs, email=self.fridge_prefs)

        # validate_email performs DNS checks; patch it during tests to avoid network calls
        with patch("Notification.dependencies.python.user_fridge_notifications_model.validate_email", return_value={"email": "test@example.com"}):
            model = UserFridgeNotificationModel(
                user_id="user_123",
                fridge_id="fridge_123",
                contact_info=contact_info,
                contact_types_status=contact_types_status,
                contact_types_preferences=contact_types_preferences,
            )

        self.assertEqual(model.user_id, "user_123")
        self.assertEqual(model.fridge_id, "fridge_123")
        # phone should be normalized to E.164
        self.assertTrue(model.contact_info.sms.startswith("+1"))

    def test_inconsistent_fields_raise_value_error(self):
        # contact_info.email set but preferences and status not set -> should raise
        contact_info = ContactInfoModel(email="test@example.com")
        contact_types_status = ContactTypeStatusModel()
        contact_types_preferences = ContactTypePreferencesModel()
        with patch("Notification.dependencies.python.user_fridge_notifications_model.validate_email", return_value={"email": "test@example.com"}):
            with self.assertRaises(ValueError):
                UserFridgeNotificationModel(
                    user_id="user_123",
                    fridge_id="fridge_123",
                    contact_info=contact_info,
                    contact_types_status=contact_types_status,
                    contact_types_preferences=contact_types_preferences,
                )

    def test_invalid_phone_raises(self):
        contact_info = ContactInfoModel(email=None, sms="not-a-number")
        contact_types_status = ContactTypeStatusModel(sms=None)
        contact_types_preferences = ContactTypePreferencesModel()

        with self.assertRaises(ValueError):
            UserFridgeNotificationModel(
                user_id="user_123",
                fridge_id="fridge_123",
                contact_info=contact_info,
                contact_types_status=contact_types_status,
                contact_types_preferences=contact_types_preferences,
            )

    def test_validate_phone_number_function(self):
        formatted = validate_phone_number("+14155552671")
        self.assertEqual(formatted, "+14155552671")


if __name__ == "__main__":
    unittest.main()
