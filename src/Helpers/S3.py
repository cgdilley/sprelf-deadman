from .Interfaces.LogMethod import LogMethod, LogLevel

import boto3
import os
from typing import Optional


def upload(filename: str,
           bucket: str,
           bucket_key: str,
           acl: str = None,
           client_kwargs: Optional[dict] = None,
           logger: LogMethod = LogMethod.null,
           profile_name: Optional[str] = None,
           **kwargs) -> dict:

    try:
        s3 = _client(client_kwargs, profile_name)
        with open(filename, "rb") as f:
            options = {
                "Bucket": bucket,
                "Key": bucket_key,
                "Body": f
            }
            if acl:
                options["ACL"] = acl
            for k, v in kwargs.items():
                options[k] = v
            return s3.put_object(**options)
    except IOError:
        raise
    except Exception as e:
        raise RuntimeError("Failed to upload file to S3", e)


def _client(client_kwargs: Optional[dict], profile_name: Optional[str]):
    kwargs = client_kwargs if client_kwargs is not None else dict()
    if profile_name:
        return boto3.Session(profile_name=profile_name).client('s3', **kwargs)
    return boto3.client('s3', **kwargs)
