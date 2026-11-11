import json
import os
import uuid
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def handler(event, context):
    try:
        payload = json.loads(event.get('body') or '')
    except (json.JSONDecodeError, TypeError):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid JSON payload'})
        }

    payload['id'] = payload.get('id', str(uuid.uuid4()))

    table.put_item(Item=payload)

    return {
        'statusCode': 201,
        'body': json.dumps({'id': payload['id']})
    }