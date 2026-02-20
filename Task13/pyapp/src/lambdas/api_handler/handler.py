import json
import boto3
from botocore.exceptions import ClientError

# Клиенты AWS
cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

# Таблицы DynamoDB (имена как в задании)
tables_table = dynamodb.Table('Tables')
reservations_table = dynamodb.Table('Reservations')

# Замени на реальные после деплоя (из AWS Console -> Cognito)
USER_POOL_ID = 'YOUR_USER_POOL_ID'  # e.g., eu-west-1_xxxxxx
CLIENT_ID = 'YOUR_APP_CLIENT_ID'  # e.g., 1abc2def3ghi4jkl5mno6pqr

def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }

def response(status, body):
    return {
        'statusCode': status,
        'headers': cors_headers(),
        'body': json.dumps(body)
    }

def is_authorized(event):
    # Простая проверка на наличие токена (для теста). В проде используй cognitojwt для верификации JWT.
    auth_header = event.get('headers', {}).get('Authorization')
    if not auth_header:
        raise ValueError('Unauthorized')
    # Здесь можно добавить полную верификацию: import cognitojwt; cognitojwt.decode(auth_header, USER_POOL_ID, CLIENT_ID)
    return True

def lambda_handler(event, context):
    path = event.get('path', '')
    method = event.get('httpMethod', '')
    body = json.loads(event.get('body', '{}')) if event.get('body') else {}

    # OPTIONS for CORS preflight
    if method == 'OPTIONS':
        return response(200, {})

    try:
        if path == '/signup' and method == 'POST':
            username = body.get('username')
            password = body.get('password')
            if not username or not password:
                return response(400, {'error': 'Username and password required'})
            cognito.sign_up(
                ClientId=CLIENT_ID,
                Username=username,
                Password=password,
                UserAttributes=[{'Name': 'email', 'Value': username}]
            )
            return response(200, {'message': 'User signed up'})

        elif path == '/signin' and method == 'POST':
            username = body.get('username')
            password = body.get('password')
            if not username or not password:
                return response(400, {'error': 'Username and password required'})
            auth_response = cognito.admin_initiate_auth(
                UserPoolId=USER_POOL_ID,
                ClientId=CLIENT_ID,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={'USERNAME': username, 'PASSWORD': password}
            )
            return response(200, auth_response['AuthenticationResult'])

        # Защищённые эндпоинты — проверка auth
        is_authorized(event)

        if path == '/tables' and method == 'POST':
            table_id = body.get('tableId')
            capacity = body.get('capacity')
            if not table_id or not capacity:
                return response(400, {'error': 'tableId and capacity required'})
            tables_table.put_item(Item={'id': table_id, 'capacity': capacity})
            return response(200, {'message': 'Table created'})

        elif path == '/tables' and method == 'GET':
            scan = tables_table.scan()
            return response(200, scan['Items'])

        elif path.startswith('/tables/') and method == 'GET':
            table_id = path.split('/')[-1]
            item = tables_table.get_item(Key={'id': table_id})
            if 'Item' in item:
                return response(200, item['Item'])
            return response(404, {'error': 'Table not found'})

        elif path == '/reservations' and method == 'POST':
            reservation_id = body.get('reservationId')
            table_id = body.get('tableId')
            date = body.get('date')
            if not reservation_id or not table_id or not date:
                return response(400, {'error': 'reservationId, tableId and date required'})
            reservations_table.put_item(Item={'id': reservation_id, 'tableId': table_id, 'date': date})
            return response(200, {'message': 'Reservation created'})

        elif path == '/reservations' and method == 'GET':
            scan = reservations_table.scan()
            return response(200, scan['Items'])

        else:
            return response(404, {'error': 'Endpoint not found'})

    except ValueError as e:
        return response(401, {'error': str(e)})
    except ClientError as e:
        return response(400, {'error': str(e)})
    except Exception as e:
        return response(500, {'error': str(e)})