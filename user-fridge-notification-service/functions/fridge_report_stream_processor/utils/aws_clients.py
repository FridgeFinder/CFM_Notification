"""
AWS client connection utilities.
"""
import os
import boto3

def get_ddb_connection():
    """Create a DynamoDB client"""
    env = os.environ.get('DEPLOYMENT_TARGET', 'aws')
    if env == 'aws':
        return boto3.client('dynamodb')
    else:
        return boto3.client('dynamodb', endpoint_url='http://localstack:4566/')

def get_ses_connection():
    """Create an SES client"""
    env = os.environ.get('DEPLOYMENT_TARGET', 'aws')
    if env == 'aws':
        return boto3.client('ses')
    else:
        return boto3.client('ses', endpoint_url='http://localstack:4566/')
