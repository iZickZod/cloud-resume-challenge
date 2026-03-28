import json
import boto3
import uuid
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

def handle_reactions(method, body):
    table = dynamodb.Table('portfolio-reactions')

    if method == 'GET':
        result = table.scan()
        data = {}
        for item in result.get('Items', []):
            pid = item['projectId']
            data[pid] = {
                'fire': int(item.get('fire', 0)),
                'clap': int(item.get('clap', 0)),
                'bulb': int(item.get('bulb', 0))
            }
        return respond(200, data)

    if method == 'POST':
        project_id = body.get('projectId')
        reaction = body.get('reaction')
        action = body.get('action')  # 'add' or 'remove'

        if not project_id or reaction not in ['fire', 'clap', 'bulb'] or action not in ['add', 'remove']:
            return respond(400, {'error': 'Invalid input'})

        if action == 'remove':
            try:
                table.update_item(
                    Key={'projectId': project_id},
                    UpdateExpression='ADD #r :delta',
                    ConditionExpression='attribute_exists(#r) AND #r >= :one',
                    ExpressionAttributeNames={'#r': reaction},
                    ExpressionAttributeValues={':delta': -1, ':one': 1}
                )
            except Exception:
                pass
        else:
            table.update_item(
                Key={'projectId': project_id},
                UpdateExpression='ADD #r :delta',
                ExpressionAttributeNames={'#r': reaction},
                ExpressionAttributeValues={':delta': 1}
            )

        item = table.get_item(Key={'projectId': project_id}).get('Item', {})
        return respond(200, {
            'fire': int(item.get('fire', 0)),
            'clap': int(item.get('clap', 0)),
            'bulb': int(item.get('bulb', 0))
        })

    return respond(405, {'error': 'Method not allowed'})


def handle_contact(method, body):
    if method != 'POST':
        return respond(405, {'error': 'Method not allowed'})

    name    = str(body.get('name',    '')).strip()[:100]
    email   = str(body.get('email',   '')).strip()[:100]
    message = str(body.get('message', '')).strip()[:2000]

    if not name or not email or not message:
        return respond(400, {'error': 'All fields required'})
    if '@' not in email or '.' not in email:
        return respond(400, {'error': 'Invalid email'})

    table = dynamodb.Table('portfolio-contact')
    table.put_item(Item={
        'id':        str(uuid.uuid4()),
        'name':      name,
        'email':     email,
        'message':   message,
        'timestamp': datetime.utcnow().isoformat()
    })
    return respond(200, {'success': True})


def handle_poll(method, body):
    table = dynamodb.Table('portfolio-poll')
    valid = ['recruiter', 'student', 'developer', 'browsing']

    if method == 'GET':
        result = table.scan()
        counts = {item['option']: int(item.get('count', 0)) for item in result.get('Items', [])}
        return respond(200, counts)

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
        result = table.scan()
        counts = {item['option']: int(item.get('count', 0)) for item in result.get('Items', [])}
        return respond(200, counts)

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

    if '/reactions' in path:
        return handle_reactions(method, body)
    if '/contact' in path:
        return handle_contact(method, body)
    if '/poll' in path:
        return handle_poll(method, body)

    return respond(404, {'error': 'Not found'})
