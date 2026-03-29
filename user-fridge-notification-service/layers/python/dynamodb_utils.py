"""DynamoDB connection utility shared across Lambda functions."""
import os
import boto3
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer


def get_ddb_connection():
    """Create a DynamoDB client; uses LocalStack when DEPLOYMENT_TARGET is not 'aws'."""
    env = os.environ.get("DEPLOYMENT_TARGET", "local")
    if env == "aws":
        return boto3.client("dynamodb")
    else:
        return boto3.client("dynamodb", endpoint_url="http://localstack:4566/")


def dict_to_dynamodb(data: dict) -> dict:
    """Convert Python dict to DynamoDB wire format."""
    serializer = TypeSerializer()
    return {k: serializer.serialize(v) for k, v in data.items()}


def dynamodb_to_dict(ddb_item: dict) -> dict:
    """Convert DynamoDB wire-format item to Python dict."""
    deserializer = TypeDeserializer()
    return {k: deserializer.deserialize(v) for k, v in ddb_item.items()}
