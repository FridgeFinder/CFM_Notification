import unittest
from user_fridge_notifications_model import (
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
            noFood=True,
            hasFood=True,
        )

    def test_model_happy_path(self):
        contact_types_preferences = ContactTypePreferencesModel(device=self.fridge_prefs, email=self.fridge_prefs)

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
        self.assertIsNone(model.contactTypePreferences.device)

    def test_patch_preferences_partial_field_update(self):
        """Test updating only specific fields within a contact type"""
        contact_prefs = ContactTypePreferencesModel(email=self.fridge_prefs)
        model = UserFridgeNotificationModel(
            userId="user_123",
            fridgeId="fridge_123",
            contactTypePreferences=contact_prefs,
        )
        
        # Update only the 'dirty' field
        model.patch_preferences({"email": {"dirty": False}})
        
        # dirty should be updated
        self.assertEqual(model.contactTypePreferences.email.dirty, False)
        # all other fields should remain unchanged
        self.assertEqual(model.contactTypePreferences.email.good, True)
        self.assertEqual(model.contactTypePreferences.email.outOfOrder, True)
        self.assertEqual(model.contactTypePreferences.email.noFood, True)

    def test_patch_preferences_update_multiple_fields(self):
        """Test updating multiple fields within a contact type"""
        contact_prefs = ContactTypePreferencesModel(email=self.fridge_prefs)
        model = UserFridgeNotificationModel(
            userId="user_123",
            fridgeId="fridge_123",
            contactTypePreferences=contact_prefs,
        )
        
        # Update multiple fields
        model.patch_preferences({
            "email": {
                "dirty": False,
                "good": False,
                "ghost": False
            }
        })
        
        # Updated fields
        self.assertEqual(model.contactTypePreferences.email.dirty, False)
        self.assertEqual(model.contactTypePreferences.email.good, False)
        self.assertEqual(model.contactTypePreferences.email.ghost, False)
        # Unchanged fields
        self.assertEqual(model.contactTypePreferences.email.outOfOrder, True)
        self.assertEqual(model.contactTypePreferences.email.noFood, True)

    def test_patch_preferences_add_new_contact_type(self):
        """Test adding a new contact type while preserving existing ones"""
        contact_prefs = ContactTypePreferencesModel(email=self.fridge_prefs)
        model = UserFridgeNotificationModel(
            userId="user_123",
            fridgeId="fridge_123",
            contactTypePreferences=contact_prefs,
        )
        
        # Add device preferences
        device_prefs = FridgePreferencesModel(
            good=False,
            dirty=False,
            outOfOrder=False,
            notAtLocation=False,
            ghost=False,
            noFood=False,
            hasFood=False,
        )
        model.patch_preferences({"device": device_prefs.model_dump()})
        
        # Email should remain unchanged
        self.assertEqual(model.contactTypePreferences.email.good, True)
        self.assertEqual(model.contactTypePreferences.email.dirty, True)
        # Device should be added
        self.assertIsNotNone(model.contactTypePreferences.device)
        self.assertEqual(model.contactTypePreferences.device.good, False)

    def test_patch_preferences_remove_contact_type(self):
        """Test removing a contact type by setting to None"""
        contact_prefs = ContactTypePreferencesModel(
            email=self.fridge_prefs,
            device=self.fridge_prefs
        )
        model = UserFridgeNotificationModel(
            userId="user_123",
            fridgeId="fridge_123",
            contactTypePreferences=contact_prefs,
        )
        
        # Remove email preferences
        model.patch_preferences({"email": None})
        
        # Email should be None
        self.assertIsNone(model.contactTypePreferences.email)
        # Device should remain
        self.assertIsNotNone(model.contactTypePreferences.device)
        self.assertEqual(model.contactTypePreferences.device.good, True)

    def test_patch_preferences_preserves_unchanged_contact_types(self):
        """Test that unmentioned contact types remain unchanged"""
        contact_prefs = ContactTypePreferencesModel(
            email=self.fridge_prefs,
            device=self.fridge_prefs
        )
        model = UserFridgeNotificationModel(
            userId="user_123",
            fridgeId="fridge_123",
            contactTypePreferences=contact_prefs,
        )
        
        # Update only email
        model.patch_preferences({"email": {"dirty": False}})
        
        # Device should be completely unchanged
        self.assertIsNotNone(model.contactTypePreferences.device)
        self.assertEqual(model.contactTypePreferences.device.good, True)
        self.assertEqual(model.contactTypePreferences.device.dirty, True)

    def test_patch_preferences_invalid_field_raises_validation_error(self):
        """Test that invalid field names raise ValidationError"""
        contact_prefs = ContactTypePreferencesModel(email=self.fridge_prefs)
        model = UserFridgeNotificationModel(
            userId="user_123",
            fridgeId="fridge_123",
            contactTypePreferences=contact_prefs,
        )
        
        # Try to update with invalid contact type name (typo)
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            model.patch_preferences({"emal": {"dirty": False}})

    def test_patch_preferences_invalid_field_in_preferences_raises_error(self):
        """Test that invalid preference field names raise ValidationError"""
        contact_prefs = ContactTypePreferencesModel(email=self.fridge_prefs)
        model = UserFridgeNotificationModel(
            userId="user_123",
            fridgeId="fridge_123",
            contactTypePreferences=contact_prefs,
        )
        
        # Try to update with invalid field name within email preferences
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            model.patch_preferences({"email": {"invalidField": False}})

    def test_patch_preferences_updates_timestamp(self):
        """Test that patch_preferences updates the updatedAt timestamp"""
        contact_prefs = ContactTypePreferencesModel(email=self.fridge_prefs)
        model = UserFridgeNotificationModel(
            userId="user_123",
            fridgeId="fridge_123",
            contactTypePreferences=contact_prefs,
        )
        
        original_updated_at = model.updatedAt
        
        # Wait a tiny bit and update
        import time
        time.sleep(0.01)
        model.patch_preferences({"email": {"dirty": False}})
        
        # updatedAt should have changed
        self.assertNotEqual(model.updatedAt, original_updated_at)