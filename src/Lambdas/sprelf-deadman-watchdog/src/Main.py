import os

import boto3
from datetime import datetime, UTC

TABLE_NAME = "SprelfDeadMan"
WARN_WINDOW = 36  # HOURS
REPORT_WINDOW = 60  # HOURS
EXPIRATION_WINDOW = 132  # HOURS
REPEAT_RATE = 24  # HOURS
SENDER = os.environ.get("AlertEmail", "deadman@service.sprelf.com")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
ses = boto3.client("ses")


def main(event, context):
    now = datetime.now(tz=UTC)
    for item in scan_all_items():
        username = item.get("Username", "")
        timestamp_str = item.get("Timestamp")
        if not timestamp_str:
            continue
        last_checkin = datetime.fromisoformat(timestamp_str)
        if last_checkin.tzinfo is None:
            last_checkin = last_checkin.replace(tzinfo=UTC)
        hours_ago = (now - last_checkin).total_seconds() / 3600

        print(f"{username} last checked in {hours_ago:.1f} hours ago (last: {timestamp_str})")
        if hours_ago > EXPIRATION_WINDOW:
            continue

        if hours_ago > REPORT_WINDOW:
            print(f"User '{username}' over report window ({REPORT_WINDOW} hours)")
            send_email(
                as_list(item.get("ReportAddresses")),
                f"{username} failed check-in",
                f"{username} last checked in {hours_ago:.1f} hours ago (last: {timestamp_str}).\n"
                f"Message or call them to ensure they're ok.  If you get no reply, they may be in trouble and need help.\n\n"
                f"This email is being sent automatically by SprelfDeadMan.  This email will repeat every {REPEAT_RATE} hours "
                f"until either {username} checks in again or {EXPIRATION_WINDOW} hours have passed since their last check-in.",
            )

        if hours_ago > WARN_WINDOW:
            print(f"User '{username}' over report window ({WARN_WINDOW} hours)")
            send_email(
                as_list(item.get("WarnAddresses")),
                f"DeadMan warning: {username}",
                f"{username} last checked in {hours_ago:.1f} hours ago (last: {timestamp_str}).\n"
                f"This is a reminder to check in.\n"
                f"If it has been more than {REPORT_WINDOW} hours since a successful "
                f"check-in, your emergency contacts will also be informed.\n\n"
                f"This email is being sent automatically by SprelfDeadMan.  This email will repeat every {REPEAT_RATE} hours "
                f"until either {username} checks in again or {EXPIRATION_WINDOW} hours have passed since their last check-in.",
            )


#


#


def as_list(value):
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def send_email(addresses, subject, body):
    if not addresses:
        return
    print(f"Sending email to {','.join(addresses)}")
    ses.send_email(
        Source=SENDER,
        Destination={"ToAddresses": addresses},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body}},
        },
    )


def scan_all_items():
    response = table.scan()
    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return items