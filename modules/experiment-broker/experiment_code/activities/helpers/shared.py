import boto3
import chaoslib
from chaoslib.exceptions import ActivityFailed
import os
from typing import Any, Dict
import logging

class ActivitiesFilter(logging.Filter):
    def __init__(self, activity):
        self.activity = activity

    def filter(self, record):
        parts = record.pathname.split(os.sep)
        if self.activity:
            record.filename = os.sep.join(parts[-2:])


def get_logger(name: str, activity: bool = True, level = logging.INFO) -> logging.Logger:
    """
    Creates a logger.

    :param name: str: The name of the logger.
    :param activity: bool: Whether the logger is being created in an activity file. Will add the first level directory to the filename since all files are 'actions', 'probes', and 'shared'.
    :param level: logging level: The logging level.

    :return: logging.Logger: The logger.
    """
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.addFilter(ActivitiesFilter(activity))
    formatter = logging.Formatter(
        fmt="[%(levelname).1s %(process)s %(asctime)s %(filename)s:%(lineno)d] %(message)s",
        datefmt="%H:%M:%S",
    )

    handler.setFormatter(formatter)
    logger.handlers = [handler]
    logger.setLevel(level)

    return logger


logger = get_logger(__name__, True)

def get_aws_client(arn, region, kind, endpoint=None):
    sts_client = boto3.client("sts")

    stsresponse = sts_client.assume_role(
        RoleArn=arn, RoleSessionName="experiment-broker"
    )
    requested_client = boto3.client(
        kind,
        region=region,
        aws_access_key_id=stsresponse["Credentials"]["AccessKeyId"],
        aws_secret_access_key=stsresponse["Credentials"]["SecretAccessKey"],
        aws_session_token=stsresponse["Credentials"]["SessionToken"],
        endpoint_url=endpoint,
    )
    return requested_client


def get_aws_resource(arn, region, kind, endpoint=None):
    sts_client = boto3.client("sts")

    stsresponse = sts_client.assume_role(
        RoleArn=arn, RoleSessionName="experiment-broker"
    )
    requested_client = boto3.resource(
        kind,
        region=region,
        aws_access_key_id=stsresponse["Credentials"]["AccessKeyId"],
        aws_secret_access_key=stsresponse["Credentials"]["SecretAccessKey"],
        aws_session_token=stsresponse["Credentials"]["SessionToken"],
        endpoint_url=endpoint,
    )
    return requested_client

def handle_pagination(client: Any, call: str, **kwargs) -> list[Dict]:
    """
    Handles pagination for AWS API Calls
    
    :param client: Any
    :param call: str
    :param **kwargs: The keyword argument for the API call
    
    :return list[dict] The list of paginated results
    """

    response = getattr(client, call)(**kwargs)
    logger.info(f"client: {client}, call: {call}, kwargs: {kwargs}")
    keys = [k for k in response.keys() if k not in ["NextToken", "ResponseMetadata"]]
    logger.info(f"keys found excluding NextToken and ResponseMetadata: {keys}")
    if len(keys) == 0:
        logger.info("no keys, returning []")
        return []
    
    key = keys[0]
    logger.info(f"Key chosen: {key}")
    results = response.get(key, [])
    logger.info(f"Num Results: {len(results)}")
    while response.get("NextToken"):
        logger.info("Found NextToken, getting new page...")
        response = getattr(client, call)(NextToken=response["NextToken", **kwargs])
        results.extend(response.get(key, []))
        logger.info(f"Num Results: {len(results)}")