# SprelfDeadMan

SprelfDeadMan is a serverless "dead man's switch" for AWS. Users check in on a regular schedule through a small web app. If a user stops checking in, the system emails the people they have configured: first a reminder to the warning contacts, then a failure notice to the report contacts.

## How it works

- A user checks in through the web frontend (`src/Frontend`), which is a static progressive web app.
- The check-in Lambda (`src/Lambdas/sprelf-deadman-checkin`) records the user's latest check-in timestamp in the `SprelfDeadMan` DynamoDB table.
- The watchdog Lambda (`src/Lambdas/sprelf-deadman-watchdog`) runs on a schedule, scans every item in the table, and compares each user's last check-in to these thresholds:

| Window | Hours | Action |
| --- | --- | --- |
| `WARN_WINDOW` | 36 | Email `WarnAddresses` a reminder to check in |
| `REPORT_WINDOW` | 60 | Email `ReportAddresses` that the user failed to check in |
| `EXPIRATION_WINDOW` | 132 | Stop sending alerts for that user |

- While a user remains overdue, alerts repeat every 24 hours (`REPEAT_RATE`) until the user checks in again or the expiration window passes.
- Emails are sent through Amazon SES. The sender address comes from the `AlertEmail` environment variable, with a default of `deadman@service.sprelf.com`.
- Infrastructure is defined in `src/Templates/stack-deadman.yaml` (AWS CloudFormation).

## Project layout

```
pyproject.toml                 Workspace root (uv)
src/
  Frontend/                    Static check-in web app (PWA)
  Helpers/                     Shared helpers: packaging/publishing (Lambda.py), S3 and user tooling
  Lambdas/
    sprelf-deadman-checkin/    Check-in Lambda
    sprelf-deadman-watchdog/   Scheduled watchdog Lambda that sends alerts
  Templates/
    stack-deadman.yaml         CloudFormation stack
```

## Requirements

- Python 3.11
- [uv](https://docs.astral.sh/uv/)
- AWS credentials with access to DynamoDB, SES, Lambda, and S3

## Setup

```powershell
uv sync
```

The root `pyproject.toml` defines a uv workspace that includes the `sprelf-deadman*` Lambda packages.

## Deployment

Lambda code is packaged and published with the `sprelf-lambda` command:

```powershell
uv run sprelf-lambda sprelf-deadman-watchdog --handler Main.main --profile <aws-profile>
```

Use `--dry-run` to build the package without uploading it, or `--help` to see all options.

## License

This project is released under the MIT License. See [LICENSE.md](LICENSE.md).
