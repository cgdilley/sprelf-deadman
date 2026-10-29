import argparse
import hashlib
import hmac
import secrets
from datetime import datetime, UTC

import boto3

TABLE_NAME = "SprelfDeadMan"


def get_pepper(session, secret_id):
    secrets_manager = session.client("secretsmanager")
    response = secrets_manager.get_secret_value(SecretId=secret_id)
    return response["SecretString"].encode()


def hash_secret(secret, pepper):
    return hmac.new(pepper, secret.encode(), hashlib.sha256).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Create a new user in the SprelfDeadMan DynamoDB table.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--warn-addresses", nargs="*", default=[])
    parser.add_argument("--report-addresses", nargs="*", default=[])
    parser.add_argument("--pepper-secret-id", required=True, help="Secrets Manager ID or ARN of the pepper")
    parser.add_argument("--secret-bytes", type=int, default=32)
    parser.add_argument("--profile", help="AWS CLI profile to use (defaults to the standard credential chain)")
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile)
    secret = secrets.token_urlsafe(args.secret_bytes)
    pepper = get_pepper(session, args.pepper_secret_id)
    hashed_secret = hash_secret(secret, pepper)

    table = session.resource("dynamodb").Table(TABLE_NAME)
    table.put_item(
        Item={
            "UserId": args.username,
            "Username": args.username,
            "Secret": hashed_secret,
            "Timestamp": datetime.now(tz=UTC).isoformat(),
            "WarnAddresses": args.warn_addresses,
            "ReportAddresses": args.report_addresses,
        }
    )

    print(f"Username: {args.username}")
    print(f"Secret: {secret}")


if __name__ == "__main__":
    main()
