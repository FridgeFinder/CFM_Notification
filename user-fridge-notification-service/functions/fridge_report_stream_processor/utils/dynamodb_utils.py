"""
DynamoDB utility functions.
"""
from boto3.dynamodb.types import TypeDeserializer

def dynamodb_to_dict(ddb_item: dict) -> dict:
    """Convert DynamoDB item to Python dict"""
    deserializer = TypeDeserializer()
    return {k: deserializer.deserialize(v) for k, v in ddb_item.items()}
