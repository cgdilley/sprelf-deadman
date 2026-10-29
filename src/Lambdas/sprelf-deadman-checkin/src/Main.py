import hashlib
import hmac
import json
import os

import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime, UTC

TABLE_NAME = "SprelfDeadMan"
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
secrets_manager = boto3.client("secretsmanager")
_pepper = None


def get_pepper():
    global _pepper
    if _pepper is None:
        response = secrets_manager.get_secret_value(SecretId=os.environ["PEPPER_SECRET_ARN"])
        _pepper = response["SecretString"].encode()
    return _pepper


def hash_secret(secret):
    return hmac.new(get_pepper(), secret.encode(), hashlib.sha256).hexdigest()


def main(event, context):
    qsp = event.get("queryStringParameters") or {}
    username = qsp.get("username", "")
    secret = qsp.get("secret", "")
    timestamp_str = qsp.get("timestamp")
    if not timestamp_str:
        timestamp = datetime.now(tz=UTC)
    else:
        timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=UTC)

    response = table.get_item(Key={"UserId": username})
    item = response.get("Item")
    if not item or not hmac.compare_digest(item.get("Secret", ""), hash_secret(secret)):
        return {"statusCode": 403,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                "body": json.dumps({"message": "Invalid username or secret"})}

    table.update_item(
        Key={"UserId": username},
        UpdateExpression="SET #ts = :ts",
        ExpressionAttributeNames={"#ts": "Timestamp"},
        ExpressionAttributeValues={":ts": timestamp.isoformat()},
    )
    return {"statusCode": 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            "body": json.dumps({"message": "Check-in recorded", "timestamp": timestamp.isoformat()})}
