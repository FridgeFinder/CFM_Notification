from pydantic import BaseModel, Field, ConfigDict
from typing import ClassVar
from typing import Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_utc_timestamp() -> str:
    """Generate ISO 8601 timestamp with Z suffix and milliseconds for frontend compatibility"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

class FridgePreferencesModel(BaseModel):
    model_config = ConfigDict(extra="forbid") # Forbid extra fields
    good: bool
    dirty: bool = True
    outOfOrder: bool = True
    notAtLocation: bool = True
    ghost: bool = True
    noFood: bool
    hasFood: bool

class ContactTypePreferencesModel(BaseModel):
    model_config = ConfigDict(extra="forbid") # Forbid extra fields
    email: Optional[FridgePreferencesModel] = None
    device: Optional[FridgePreferencesModel] = None

class UserFridgeNotificationModel(BaseModel):
    #NOTE: MIN_ID_LENGTH and MAX_ID_LENGTH is used in a different service as well, should maybe set as an environment field on aws
    MIN_ID_LENGTH: ClassVar[int] = 3
    MAX_ID_LENGTH: ClassVar[int] = 100
    userId: str = Field(..., min_length = MIN_ID_LENGTH, max_length = MAX_ID_LENGTH)
    fridgeId: str = Field(..., min_length = MIN_ID_LENGTH, max_length = MAX_ID_LENGTH)
    contactTypePreferences: ContactTypePreferencesModel
    createdAt: str = Field(default_factory=get_utc_timestamp)
    updatedAt: str = Field(default_factory=get_utc_timestamp) 
    #last_notified?
    #last_emailed?

    def update_preferences(self, contactTypePreferences: dict) -> None:
        """
        Update contact type preferences and refresh the updatedAt timestamp.
        
        Args:
            contactTypePreferences: New preferences dict to validate and set
        """
        # Pydantic will validate the input when we create the model
        self.contactTypePreferences = ContactTypePreferencesModel(**contactTypePreferences)
        self.updatedAt = get_utc_timestamp()
    
    def patch_preferences(self, partialContactTypePreferences: dict) -> None:
        """
        Partially update contact type preferences, only modifying fields that are provided.
        Preserves existing values for fields not included in the partial update.
        
        Args:
            partialContactTypePreferences: Partial preferences dict with only the fields to update
            
        Examples:
            # Update only email preferences, leaving device unchanged
            model.patch_preferences({"email": {"dirty": True, "good": False, ...}})
            
            # Update only the 'dirty' field within email preferences
            model.patch_preferences({"email": {"dirty": True}})
        """
        # Start with current preferences as dict
        current_prefs = self.contactTypePreferences.model_dump()
        
        # Iterate over provided contact types (e.g., 'email', 'device')
        for contact_type, partial_prefs in partialContactTypePreferences.items():
            if partial_prefs is None:
                current_prefs[contact_type] = None
                continue

            if current_prefs.get(contact_type) is not None:
                # Contact type exists, merge the partial preferences
                for field, value in partial_prefs.items():
                    current_prefs[contact_type][field] = value
            else:
                # Contact type doesn't exist yet, validate and set it
                # Pydantic will validate this has all required fields
                current_prefs[contact_type] = partial_prefs
        
        # Validate the merged result and update
        self.contactTypePreferences = ContactTypePreferencesModel(**current_prefs)
        self.updatedAt = get_utc_timestamp()
