from .Interfaces.LogMethod import LogMethod, LogLevel
from . import S3

import os
import boto3
import zipfile
import json
import base64
import shutil

from typing import Optional, Iterable, Tuple, Dict, Union

PRE_PACKAGED_MODULES = ["boto3", "botocore", "jmespath", "python-dateutil", "urllib3",
                        "s3transfer", "Jinja2", "MarkupSafe", "wheel", "six"]


def publish(lambda_name: str,
            handler: str,
            build_dir: str = "_build",
            src_dir: str = "src",
            requirements_file: str = "requirements.txt",
            environment_file: str = "local.env",
            tags_file: str = "tags.toml",
            package_file: str = "package.zip",
            code_bucket: str = "sprelf-lambda-zips",
            code_bucket_path: str = "",
            publish_after: bool = True,
            dry_run: bool = False,
            delete_lock: bool = False,
            aws_client_kwargs: Optional[dict] = None,
            skip_dependencies: bool = False,
            skip_package_upload: bool = False,
            local_libs: Dict[str, str] = None,
            cwd: Optional[str] = None,
            aws_profile: Optional[str] = None,
            logger: LogMethod = LogMethod.null):
    #
    if cwd:
        os.chdir(cwd)
    else:
        os.chdir(f"./src/Lambdas/{lambda_name}")

    if not skip_package_upload:
        if not skip_dependencies:
            logger("Packaging dependencies", heading="Lambda", level=LogLevel.VERBOSE)
            package_dependencies(build_dir=build_dir,
                                 requirements_file=requirements_file,
                                 cwd=None,
                                 delete_lock=delete_lock,
                                 logger=logger)

        if local_libs is not None and len(local_libs) > 0:
            logger("Copying local libraries", heading="Lambda", level=LogLevel.VERBOSE)
            copy_local_libs(build_dir=build_dir,
                            cwd=None,
                            local_libs=local_libs,
                            logger=logger)

        logger("Zipping package contents", heading="Lambda", level=LogLevel.VERBOSE)
        zip_everything(package_file=package_file,
                       build_dir=build_dir,
                       src_dir=src_dir,
                       cwd=None,
                       logger=logger)

    logger("Updating AWS function", heading="Lambda", level=LogLevel.VERBOSE)
    upload_to_lambda(lambda_name=lambda_name,
                     handler=handler,
                     package_file=package_file,
                     environment_file=environment_file,
                     code_bucket=code_bucket,
                     code_bucket_path=code_bucket_path,
                     tags_file=tags_file,
                     publish_after=publish_after,
                     dry_run=dry_run,
                     skip_package_upload=skip_package_upload,
                     cwd=None,
                     client_kwargs=aws_client_kwargs,
                     profile_name=aws_profile,
                     logger=logger)


def main(argv: Optional[list] = None):
    import argparse

    parser = argparse.ArgumentParser(description="Package and publish an AWS Lambda function.")
    parser.add_argument("lambda_name", help="Name of the AWS Lambda function to update")
    parser.add_argument("--handler", help="Handler of the Lambda function, e.g. Main.main", default="Main.main")
    parser.add_argument("--build-dir", default="_build")
    parser.add_argument("--src-dir", default="src")
    parser.add_argument("--requirements-file", default="requirements.txt")
    parser.add_argument("--environment-file", default="local.env")
    parser.add_argument("--tags-file", default="tags.toml")
    parser.add_argument("--package-file", default="package.zip")
    parser.add_argument("--code-bucket", default="sprelf-lambda-zips")
    parser.add_argument("--code-bucket-path", default="")
    parser.add_argument("--no-publish-after", dest="publish_after", action="store_false")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delete-lock", action="store_true")
    parser.add_argument("--skip-dependencies", action="store_true")
    parser.add_argument("--skip-package-upload", action="store_true")
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--profile", dest="aws_profile", default=None, help="AWS CLI profile to use for authentication")
    args = parser.parse_args(argv)

    publish(lambda_name=args.lambda_name,
            handler=args.handler,
            build_dir=args.build_dir,
            src_dir=args.src_dir,
            requirements_file=args.requirements_file,
            environment_file=args.environment_file,
            tags_file=args.tags_file,
            package_file=args.package_file,
            code_bucket=args.code_bucket,
            code_bucket_path=args.code_bucket_path,
            publish_after=args.publish_after,
            dry_run=args.dry_run,
            delete_lock=args.delete_lock,
            skip_dependencies=args.skip_dependencies,
            skip_package_upload=args.skip_package_upload,
            cwd=args.cwd,
            aws_profile=args.aws_profile)


if __name__ == "__main__":
    main()


#


def package_dependencies(build_dir: str, requirements_file: str,
                         cwd: Optional[str] = None,
                         delete_lock: bool = False,
                         logger: LogMethod = LogMethod.null):
    if cwd:
        os.chdir(cwd)

    try:
        os.mkdir(build_dir)
    except OSError:
        pass

    os.system(f"uv export --no-hashes --no-emit-project --format requirements-txt > \"{requirements_file}\"")

    with open(requirements_file, "r", encoding="utf-8") as f:
        requirements = f.readlines()
    requirements = [req.strip() for req in requirements if not any(req.startswith(ppm) for ppm in PRE_PACKAGED_MODULES)]
    with open(requirements_file, "w", encoding="utf-8") as f:
        f.write("\n".join(requirements))

    os.system(f"uv pip install --upgrade -r \"{requirements_file}\" --target \"{build_dir}\"")

    for path in os.listdir(build_dir):
        for ppm in PRE_PACKAGED_MODULES:
            if path.startswith(ppm):
                abs_path = os.path.join(build_dir, path)
                if os.path.isdir(abs_path):
                    shutil.rmtree(abs_path)
                else:
                    os.remove(abs_path)

    if delete_lock and os.path.exists("uv.lock"):
        os.remove("uv.lock")


#


def copy_local_libs(build_dir: str,
                    local_libs: Dict[str, str],
                    cwd: Optional[str] = None,
                    logger: LogMethod = LogMethod.null):
    if cwd:
        os.chdir(cwd)

    for lib, path in local_libs.items():
        logger(f" - {lib}", heading="Lambda", level=LogLevel.VERBOSE)
        target = os.path.join(build_dir, lib)
        if os.path.exists(target):
            shutil.rmtree(target)
        shutil.copytree(path, target)


#


def zip_everything(package_file: str, build_dir: str, src_dir: str,
                   cwd: Optional[str] = None,
                   logger: LogMethod = LogMethod.null):
    if cwd:
        os.chdir(cwd)

    if os.path.exists(package_file):
        os.remove(package_file)

    with zipfile.ZipFile(package_file, mode="w") as zf:
        _add_dir_to_zip(zf, build_dir)
        _add_dir_to_zip(zf, src_dir)


def _lambda_client(client_kwargs: Optional[dict], profile_name: Optional[str]):
    kwargs = client_kwargs if client_kwargs else dict()
    if profile_name:
        return boto3.Session(profile_name=profile_name).client('lambda', **kwargs)
    return boto3.client('lambda', **kwargs)


def _add_dir_to_zip(zf: zipfile.ZipFile, directory: str):
    for root, dirs, files in os.walk(directory):
        relative_root = root[len(directory):].strip(os.path.sep)
        for name in files:
            zf.write(os.path.join(root, name), arcname=os.path.join(relative_root, name))


#


def upload_to_lambda(lambda_name: str,
                     handler: str,
                     package_file: str,
                     code_bucket: str,
                     code_bucket_path: str,
                     environment_file: Optional[str] = None,
                     tags_file: Optional[str] = None,
                     publish_after: bool = True,
                     dry_run: bool = False,
                     skip_package_upload: bool = False,
                     cwd: Optional[str] = None,
                     client_kwargs: Optional[dict] = None,
                     profile_name: Optional[str] = None,
                     logger: LogMethod = LogMethod.null):
    if cwd:
        os.chdir(cwd)

    lamb = _lambda_client(client_kwargs, profile_name)

    #

    logger("Getting function info", heading="Lambda", level=LogLevel.VERBOSE)
    info = lamb.get_function(FunctionName=lambda_name)["Configuration"]

    #

    zip_name = lambda_name + ".zip"
    s3_key = (code_bucket_path.rstrip("/") + "/" + zip_name) if code_bucket_path else zip_name

    if not skip_package_upload:
        logger("Uploading package", heading="Lambda", level=LogLevel.VERBOSE, log_depth=1)

        S3.upload(filename=package_file,
                  bucket=code_bucket,
                  bucket_key=s3_key,
                  client_kwargs=client_kwargs,
                  profile_name=profile_name,
                  logger=logger)

    #

    logger("Updating function", heading="Lambda", level=LogLevel.VERBOSE, log_depth=1)
    response = lamb.update_function_code(FunctionName=lambda_name,
                                         S3Bucket=code_bucket,
                                         S3Key=s3_key,
                                         Publish=publish_after,
                                         DryRun=dry_run)

    #

    if environment_file:
        if not os.path.exists(environment_file):
            logger("Cannot find environment file.  Skipping environment config.", heading="Lambda", level=LogLevel.WARN)
        else:
            logger("Updating configuration", heading="Lambda", level=LogLevel.VERBOSE, log_depth=1)
            with open(environment_file, "r", encoding="utf-8") as f:
                env = {
                    key.strip(): value.strip()
                    for key, value in (tuple(line.split("=", maxsplit=1)) for line in f.readlines() if "=" in line)
                }
            response = lamb.update_function_configuration(FunctionName=lambda_name,
                                                          Handler=handler,
                                                          Environment={
                                                              "Variables": env
                                                          })

    #


#


def run(lambda_name: str,
        arguments: dict,
        dry_run: bool = False,
        include_logs: bool = False,
        logger: LogMethod = LogMethod.null,
        client_kwargs: Optional[dict] = None,
        profile_name: Optional[str] = None) -> dict:

    lamb = _lambda_client(client_kwargs, profile_name)

    payload = json.dumps(arguments).encode("utf-8")

    options = {
        "FunctionName": lambda_name,
        "Payload": payload,
        "InvocationType": "DryRun" if dry_run else "RequestResponse"
    }
    if include_logs:
        options["LogType"] = "Tail"

    logger(f"Invoking lambda function '{lambda_name}'...", heading="Lambda", level=LogLevel.VERBOSE)
    response = lamb.invoke(**options)

    if "Payload" in response and response["Payload"]:
        response["Payload"] = json.loads(response['Payload'].read().decode("utf-8"))

    if include_logs and "LogResult" in response:
        log_bytes = base64.decodebytes(response["LogResult"].encode("ascii"))
        log_string = log_bytes.decode("utf-8")
        response["LogResult"] = log_string.splitlines()

    if "ResponseMetadata" in response:
        del response["ResponseMetadata"]

    return response
