"""
Firebase Admin SDK initialization and management.
"""
import json
import logging
import os
import boto3
import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger()

def initialize_firebase():
    """Initialize Firebase Admin SDK (called once per Lambda container)"""
    deployment_target = os.environ.get('DEPLOYMENT_TARGET', 'aws')
    
    try:
        # Only initialize if not already initialized
        if not firebase_admin._apps:
            project_id = None
            
            if deployment_target == 'aws':
                # AWS: load from Secrets Manager
                secret_name = os.environ['FIREBASE_SECRET_NAME']
                secrets_client = boto3.client('secretsmanager')
                
                try:
                    secret = secrets_client.get_secret_value(SecretId=secret_name)
                    cred_dict = json.loads(secret['SecretString'])
                    cred = credentials.Certificate(cred_dict)
                    project_id = cred_dict.get('project_id')
                except Exception as e:
                    logger.error(f'Failed to load Firebase credentials from Secrets Manager: {e}')
                    raise RuntimeError(f'Firebase credentials not found in Secrets Manager: {secret_name}') from e
            else:
                # Local development: use credentials from file
                cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
                
                if cred_path:
                    with open(cred_path, 'r') as f:
                        cred_dict = json.load(f)
                    cred = credentials.Certificate(cred_dict)
                    project_id = cred_dict.get('project_id')
                else:
                    logger.warning('No Firebase credentials configured for local development - push notifications will be skipped')
                    return
            
            # Initialize with explicit project_id
            firebase_admin.initialize_app(cred, options={'projectId': project_id})
            logger.info(f'Firebase Admin SDK initialized successfully for project: {project_id}')
        
    except Exception as e:
        logger.error(f'Failed to initialize Firebase: {e}')
        # Fail fast in AWS environments, allow graceful degradation in local dev
        if deployment_target != 'local':
            raise RuntimeError('Firebase initialization failed - check credentials and configuration') from e
