import sys

import boto3
import logging
import random
import time
import inspect
import json
from pprint import pformat
from typing import Literal
import botocore.exceptions

handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

logging.basicConfig(level=logging.ERROR)


def get_cloudwatch_metric_alarm_status(cloudwatch_alarm_name):
    """Get a str of cloudwatch status from a given Cloudwatch alarm name."""

    session = boto3.Session()
    cloudwatch = session.client("cloudwatch", "us-east-1")

    cloudwatch_alarm_status = cloudwatch.describe_alarms(
        AlarmNames=[cloudwatch_alarm_name]
    )
    return_value = cloudwatch_alarm_status["MetricAlarms"][0]["StateValue"]

    return return_value


def get_task_cloudwatch_logs(
    region: str,
    target: str,
):
    function_name = inspect.stack()[0][3]
    cloudtrail_client = boto3.client("cloudtrail", region_name=region)
    logs_client = boto3.client("logs", region_name=region)

    task_id = target.split("/")[-1]

    logger.info(
        f"{function_name} - Finding CloudTrail CreateLogStream event for task {task_id}."
    )
    log_group_name = None
    log_stream_name = None

    response = cloudtrail_client.lookup_events(
        LookupAttributes=[{"AttributeKey": "Username", "AttributeValue": task_id}]
    )

    if response["Events"]:
        events = [
            event
            for event in response["Events"]
            if event["EventName"] == "CreateLogStream"
        ]

        if events:
            log_group_name = json.loads(events[0]["CloudTrailEvent"])[
                "requestParameters"
            ]["logGroupName"]
            log_stream_name = json.loads(events[0]["CloudTrailEvent"])[
                "requestParameters"
            ]["logStreamName"]

    logs = []

    if log_group_name and log_stream_name:
        logger.info(
            f"{function_name} - Getting log events for log stream {log_stream_name}."
        )

        response = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
        )

        if response["events"]:
            logs = response["events"]

    return logs
