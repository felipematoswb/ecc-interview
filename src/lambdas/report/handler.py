import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

def handler(event, context):
    now = datetime.now(ZoneInfo('Europe/Lisbon'))

    days_since_saturday = (now.weekday() - 5) % 7
    end_period = (now - timedelta(days=days_since_saturday)).replace(
        hour=23, minute=0, second=0, microsecond=0
    )
    
    if end_period > now:
        end_period -= timedelta(days=7)
        
    start_period = end_period - timedelta(days=7)

    total_items = 0
    scan_kwargs = {
        'FilterExpression': Attr('created_at').between(
            start_period.isoformat(), 
            end_period.isoformat()
        ),
        'Select': 'COUNT'
    }

    while True:
        response = dynamodb.Table(os.environ['TABLE_NAME']).scan()
        total_items += response.get('Count', 0)
        
        if 'LastEvaluatedKey' not in response:
            break
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    report = {
        'start_period': start_period.isoformat(),
        'end_period': end_period.isoformat(),
        'total_created': total_items,
        'executed_at': now.isoformat()
    }

    file_key = f"weekly/report_{end_period.strftime('%Y-%m-%d')}.json"
    
    s3.put_object(
        Bucket=os.environ['BUCKET_NAME'],
        Key=file_key,
        Body=json.dumps(report, indent=2),
        ContentType='application/json'
    )

    return report