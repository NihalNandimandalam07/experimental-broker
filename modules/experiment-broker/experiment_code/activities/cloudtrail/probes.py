import boto3
import logging
import random
import time
import inspect
import json
import datetime
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

from activities.cloudtrail.shared import attempt_retry


def assert_cloudtrail_events_occurred(
    region: str,
    event_names: list[str],
    start_time: datetime = None,
    end_time: datetime = None,
    filter_type: Literal[
        "EventId",
        "EventName",
        "ReadOnly",
        "Username",
        "ResourceType",
        "ResourceName",
        "EventSource",
        "AccessKeyId",
        None,
    ] = None,
    filter_value: str = None,
    retry: bool = False,
    max_duration_to_iterate: int = 300,
    sleep_duration: int = 15,
):
    function_name = inspect.stack()[0][3]
    cloudtrail_client = boto3.client("cloudtrail", region_name=region)

    if filter_type and filter_type not in [
        "EventId",
        "EventName",
        "ReadOnly",
        "Username",
        "ResourceType",
        "ResourceName",
        "EventSource",
        "AccessKeyId",
    ]:
        error_log = f"{function_name} - Invalid filter type: {filter_type}. Needs to be one of 'EventId', 'EventName', 'ReadOnly', 'Username', 'ResourceType', 'ResourceName', 'EventSource', 'AccessKeyId', or None."
        logger.error(error_log)
        raise ValueError(error_log)

    if end_time and start_time and end_time < start_time:
        error_log = f"{function_name} - EndTime is before StartTime."
        logger.error(error_log)
        raise ValueError(error_log)

    if filter_type and not filter_value:
        warning_log = "Filter type provided but no filter value. Ignoring filter type."
        logger.warning(warning_log)

    events = []
    current_iteration_time = 0
    event_index = 0
    while event_index < len(event_names):
        event_name = event_names[event_index]
        lookup_attributes = {}

        if filter_type and filter_value:
            lookup_attributes["LookupAttributes"] = [
                {
                    "AttributeKey": filter_type,
                    "AttributeValue": filter_value,
                }
            ]

        end_time_start_time = {}
        if start_time:
            end_time_start_time["StartTime"] = start_time
        if end_time:
            end_time_start_time["EndTime"] = end_time

        response = cloudtrail_client.lookup_events(
            **lookup_attributes,
            **end_time_start_time,
        )

        if event_name in [event["EventName"] for event in response["Events"]]:
            logger.info(
                f"{function_name} - Found CloudTrail event for EventName {event_name}."
            )
            event_index += 1
            time.sleep(2)
            current_iteration_time += 2
            continue

        else:
            log = f"No CloudTrail event found for EventName {event_name}."
            attempt_retry(
                log=log,
                retry=retry,
                current_iteration_time=current_iteration_time,
                max_duration_to_iterate=max_duration_to_iterate,
                sleep_duration=sleep_duration,
            )
            current_iteration_time += sleep_duration
