import logging
import os
import traceback
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.retries import bucket
from chaosaws import aws_client
from chaosaws.types import AWSResponse
from chaoslib.exceptions import FailedActivity
from chaoslib.types import Configuration
from logzero import logger

__all__ = ["get_object", "get_configuration_state"]

my_config = Config(
    signature_version="s3v4", retries={"max_attempts": 10, "mode": "standard"}
)


def put_object(bucket_name, key, contents, config=None):
    s3_client = boto3.client("s3", config=my_config)
    try:
        response = s3_client.put_object(Body=contents, Bucket=bucket_name, Key=key)
    except Exception:
        exc_str = traceback.format_exc()
        logger.error(f"Exception putting object to S3: {exc_str}")


def create_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client("s3", config=my_config)

    logger.error(f"{s3_client.meta.region_name}")

    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response


def get_object(
    bucket_name: str, filename: str, configuration: Configuration, region="us-east-1"
) -> AWSResponse:
    """Returns an S3 object from the specified bucket

    :param bucket_name: An S3 bucket
    :param filename: Filename of object to retrieve
    :returns: boto3 s3.Object
    """
    if not bucket_name or not filename:
        raise FailedActivity(
            "To load an object from an S3 bucket you must specify the"
            " bucket_name and filename."
        )
    if not configuration:
        region = os.environ.get(
            "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        )
        configuration = {"aws_region": region}
    client = boto3.resource("s3", config=my_config)
    obj = client.Object(bucket_name, f"{filename}")

    if not obj:
        raise FailedActivity(
            "Unable to load S3 object arn:aws:s3:::%s/%s" % (bucket_name, filename)
        )

    return obj


def get_configuration_state(filename: str, configuration: Configuration) -> AWSResponse:
    """Shared function for configuration state management that will return an
    S3 object

      :param filename: A filename to retrieve from S3
      :param configuration: A configuration dict
      :returns: boto3 s3.Object
    """
    return get_object(configuration["state_bucket"], filename, configuration)
