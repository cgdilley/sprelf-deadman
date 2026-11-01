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


def main(event, context):
    qsp = event.get("queryStringParameters") or {}
    user_id = qsp.get("userId", "")
    secret = qsp.get("secret", "")
    timestamp_str = qsp.get("timestamp")
    if not isinstance(timestamp_str, str):
        timestamp = datetime.now(tz=UTC)
    else:
        timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=UTC)

    response = table.get_item(Key={"UserId": user_id})
    item = response.get("Item")
    if not item or not hmac.compare_digest(item.get("Secret", ""), hash_secret(secret)):
        print(f"Invalid user ID or secret:  (UserId={user_id}, Secret (Last 4)={secret[-4:]})")
        return {"statusCode": 403,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                "body": json.dumps({"message": "Invalid user ID or secret"})}

    table.update_item(
        Key={"UserId": user_id},
        UpdateExpression="SET #ts = :ts",
        ExpressionAttributeNames={"#ts": "Timestamp"},
        ExpressionAttributeValues={":ts": timestamp.isoformat()},
    )
    print(f"Updated check-in timestamp for user ID '{user_id}' to '{timestamp.isoformat()}'")
    return {"statusCode": 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            "body": json.dumps({"message": "Check-in recorded", "timestamp": timestamp.isoformat()})}


#


#


def get_pepper() -> bytes:
    global _pepper
    if _pepper is None:
        response = secrets_manager.get_secret_value(SecretId=os.environ["PEPPER_SECRET_ARN"])
        _pepper = response["SecretString"].encode()
    return _pepper


def hash_secret(secret: str) -> str:
    return hmac.new(get_pepper(), secret.encode(), hashlib.sha256).hexdigest()
