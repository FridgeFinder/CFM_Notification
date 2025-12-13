import json
import logging
from typing import Dict, Any
from aws_lambda_powertools.utilities.data_classes import DynamoDBStreamEvent
from aws_lambda_powertools.utilities.typing import LambdaContext

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Process DynamoDB Stream events from FridgeReportStream.
    Logs the deserialized database data as JSON.
    
    Args:
        event: DynamoDB Stream event
        context: Lambda context
        
    Returns:
        Dict with processing status
    """
    # Parse the event using DynamoDBStreamEvent
    stream_event = DynamoDBStreamEvent(event)
    
    # Convert records generator to list to get count
    records = list(stream_event.records)
    logger.info(f"Processing {len(records)} records from DynamoDB Stream")
    
    processed_records = []
    
    for record in records:
        logger.info(f"Event ID: {record.event_id}")
        logger.info(f"Event Name: {record.event_name}")
        logger.info(f"Event Source: {record.event_source}")
        logger.info(f"Event Version: {record.event_version}")
        
        # Prepare record data
        record_data = {
            "event_id": record.event_id,
            "event_name": record.event_name,
            "event_source": record.event_source,
            "aws_region": record.aws_region,
            "dynamodb": {}
        }
        
        # Get the DynamoDB data (stream only sends NEW_IMAGE)
        if record.dynamodb and record.dynamodb.new_image:
            new_image = record.dynamodb.new_image
            record_data["dynamodb"]["new_image"] = new_image
            
            # Log the deserialized data as JSON
            logger.info(f"Fridge Report Data (deserialized): {json.dumps(new_image, indent=2, default=str)}")
            
            # Log keys
            if record.dynamodb.keys:
                keys = record.dynamodb.keys
                record_data["dynamodb"]["keys"] = keys
                logger.info(f"Keys: {json.dumps(keys, indent=2, default=str)}")
        
        # Log the complete record as JSON
        logger.info(f"Complete Record Data: {json.dumps(record_data, indent=2, default=str)}")
        
        processed_records.append(record_data)
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Successfully processed DynamoDB stream records",
            "records_processed": len(processed_records)
        })
    }
