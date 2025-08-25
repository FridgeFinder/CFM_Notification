

from pydantic import BaseModel, field_validator, Field, model_validator, ConfigDict
from typing import ClassVar
from enum import Enum
import phonenumbers
import boto3
import os
from email_validator import validate_email
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_ddb_connection(env: str = os.getenv("Environment", "")) -> "botocore.client.DynamoDB":
    ddbclient = ""
    if env == "local":
        ddbclient = boto3.client("dynamodb", endpoint_url="http://localstack:4566/")
    else:
        ddbclient = boto3.client("dynamodb")
    return ddbclient

class ContactTypeStatusEnum(Enum):
    START = "start"
    PAUSED = "pause"
    STOP = "stop"

class FridgePreferencesModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    good: bool
    dirty: bool
    out_of_order: bool
    not_at_location: bool
    ghost: bool
    food_level_0: bool
    food_level_1: bool
    food_level_2: bool
    food_level_3: bool
    cleaned: bool #TODO: need to update fridge report to accept a "cleaned" report.

class ContactTypePreferencesModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Optional[FridgePreferencesModel] = None
    sms: Optional[FridgePreferencesModel] = None
    device: Optional[FridgePreferencesModel] = None

class ContactInfoModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Optional[str] = None
    sms: Optional[str] = None
    device: Optional[str] = None

class ContactTypeStatusModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Optional[ContactTypeStatusEnum] = None
    sms: Optional[ContactTypeStatusEnum] = None
    device: Optional[ContactTypeStatusEnum] = None

class UserFridgeNotificationModel(BaseModel):
    #NOTE: MIN_ID_LENGTH and MAX_ID_LENGTH is used in a different service as well, should maybe set as an environment field on aws
    STAGE: ClassVar[str] = os.getenv("Stage")
    TABLE_NAME: ClassVar[str] = f"user_fridge_notifications_{STAGE}"
    MIN_ID_LENGTH: ClassVar[int] = 3
    MAX_ID_LENGTH: ClassVar[int] = 100
    user_id: str = Field(..., min_length = MIN_ID_LENGTH, max_length = MAX_ID_LENGTH)
    fridge_id: str = Field(..., min_length = MIN_ID_LENGTH, max_length = MAX_ID_LENGTH)
    contact_info: ContactInfoModel
    contact_types_status: ContactTypeStatusModel
    contact_types_preferences: ContactTypePreferencesModel
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)        

    @field_validator('contact_info')
    @classmethod
    def validate_contact_info(cls, contact_info: ContactInfoModel) -> ContactInfoModel:        
        if contact_info.email:
            validate_email(contact_info.email)
        if contact_info.sms:
            validate_phone_number(phone_number=contact_info.sms)     
        if contact_info.device:
            validate_device(device=contact_info.device)
        return contact_info
    

    @model_validator(mode="after")
    def validate_preferences_vs_status(self) -> "UserFridgeNotificationModel":
        field_names = ContactTypeStatusModel.model_fields.keys()

        for field in field_names:
            values = [
                getattr(self.contact_types_status, field, None),
                getattr(self.contact_types_preferences, field, None),
                getattr(self.contact_info, field, None),
            ]

            #If ANY of the values are set then ALL of the values must be set
            if any(values) and not all(values):
                raise ValueError(
                    f"Inconsistent {field}: all three (status, preferences, info) "
                    f"must be set or all must be unset. Got {values}"
                )

        return self

    
def validate_phone_number(phone_number: str) -> str:
    try:
        number = phonenumbers.parse(phone_number, None)
    except phonenumbers.NumberParseException as e:
        raise ValueError(f"Invalid phone number format: {e}")

    if not phonenumbers.is_valid_number(number):
        raise ValueError("Phone number is not valid")

    if phonenumbers.region_code_for_number(number) != "US":
        raise ValueError("Only US phone numbers are allowed")

    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)

def validate_device(device: str) -> str:
    #TODO: validate device. Don't know if we'll need this but keeping it here as a reminder
    #NOTE: for devices we should consider adding a separate devices table
    #.. but device preferences remain the same across all devices. We will probably query on user_id to get all the user's devices
    #.. but lets discuss when push notifications gets built out on mobile app
    return device