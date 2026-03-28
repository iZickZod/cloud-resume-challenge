import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-2')

def respond(status, body):
    return {
        'statusCode': status,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body, default=str)
    }

def scan_poll_counts(table):
    result = table.scan()
    return {item['option']: int(item.get('count', 0)) for item in result.get('Items', [])}


def handle_poll(method, body):
    table = dynamodb.Table('portfolio-poll')
    valid = ['recruiter', 'student', 'developer', 'browsing', 'other']

    if method == 'GET':
        return respond(200, scan_poll_counts(table))

    if method == 'POST':
        option = body.get('option')
        if option not in valid:
            return respond(400, {'error': 'Invalid option'})

        table.update_item(
            Key={'option': option},
            UpdateExpression='ADD #c :one',
            ExpressionAttributeNames={'#c': 'count'},
            ExpressionAttributeValues={':one': 1}
        )
        return respond(200, scan_poll_counts(table))

    return respond(405, {'error': 'Method not allowed'})


def lambda_handler(event, context):
    path   = event.get('rawPath', event.get('path', '/'))
    method = event.get('requestContext', {}).get('http', {}).get('method',
             event.get('httpMethod', 'GET')).upper()

    if method == 'OPTIONS':
        return respond(200, {})

    body = {}
    if event.get('body'):
        try:
            body = json.loads(event['body'])
        except Exception:
            pass

    if '/poll' in path:
        return handle_poll(method, body)

    return respond(404, {'error': 'Not found'})
