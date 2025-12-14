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
    foodLevel0: bool
    foodLevel1: bool
    foodLevel2: bool
    foodLevel3: bool

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