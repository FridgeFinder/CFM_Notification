import unittest
from datetime import datetime
from unittest.mock import patch
from Notification.dependencies.python.user_fridge_notifications_model import (
    UserFridgeNotificationModel,
    ContactTypePreferencesModel,
    FridgePreferencesModel,
)

class TestUserFridgeNotificationModel(unittest.TestCase):
    def setUp(self):
        # reusable valid fridge preferences
        self.fridge_prefs = FridgePreferencesModel(
            good=True,
            dirty=True,
            outOfOrder=True,
            notAtLocation=True,
            ghost=True,
            foodLevel0=True,
            foodLevel1=True,
            foodLevel2=True,
            foodLevel3=True,
            cleaned=True,
        )

    def test_model_happy_path(self):
        contact_types_preferences = ContactTypePreferencesModel(sms=self.fridge_prefs, email=self.fridge_prefs)

        model = UserFridgeNotificationModel(
            userId="user_123",
            fridgeId="fridge_123",
            contactTypePreferences=contact_types_preferences,
        )

        self.assertEqual(model.userId, "user_123")
        self.assertEqual(model.fridgeId, "fridge_123")
        self.assertIsNotNone(model.contactTypePreferences)
        self.assertEqual(model.contactTypePreferences.email.good, True)

    def test_empty_preferences(self):
        # Test with empty preferences
        contact_types_preferences = ContactTypePreferencesModel()
        
        model = UserFridgeNotificationModel(
            userId="user_123",
            fridgeId="fridge_123",
            contactTypePreferences=contact_types_preferences,
        )
        
        self.assertEqual(model.userId, "user_123")
        self.assertEqual(model.fridgeId, "fridge_123")
        self.assertIsNone(model.contactTypePreferences.email)
        self.assertIsNone(model.contactTypePreferences.sms)
        self.assertIsNone(model.contactTypePreferences.device)


if __name__ == "__main__":
    unittest.main()
