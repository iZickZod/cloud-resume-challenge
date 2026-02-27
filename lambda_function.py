import json
import boto3
import hashlib

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('resume-visitor-counter')

def hash_ip(ip):
    """Hash the IP address using SHA-256 for privacy — we can still detect duplicates without storing the raw IP."""
    return hashlib.sha256(ip.encode()).hexdigest()

def lambda_handler(event, context):
    # Get visitor IP from request context
    ip = event.get('requestContext', {}).get('http', {}).get('sourceIp', 'unknown')
    
    # Hash the IP — never store raw IPs
    hashed_ip = hash_ip(ip)
    
    # Get current record from DynamoDB
    response = table.get_item(Key={'id': 'counter'})
    item = response['Item']
    current_count = int(item['count'])
    visitors = item['visitors']
    
    # Only count if this hashed IP hasn't visited before
    if hashed_ip not in visitors:
        visitors.add(hashed_ip)
        current_count += 1
        table.update_item(
            Key={'id': 'counter'},
            UpdateExpression='SET #c = :count, visitors = :visitors',
            ExpressionAttributeNames={'#c': 'count'},
            ExpressionAttributeValues={
                ':count': current_count,
                ':visitors': visitors
            }
        )
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'count': current_count})
    }
