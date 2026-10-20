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


def attempt_retry(
    log: str,
    retry: bool,
    current_iteration_time: int,
    max_duration_to_iterate: int,
    sleep_duration: int,
):
    """
    Attempt to retry the function if retry is True and the retry_number is less than max_duration_to_iterate.


    Args:
        log (str): log message
        retry (bool): Retry flag
        current_iteration_time (int): Current iteration time in seconds
        max_duration_to_iterate (int): Maximum duration to attempt iterations in seconds
        sleep_duration (int): sleep duration time in seconds

    Returns:
        int: Retry number if not max_duration_to_iterate, else raise AssertionError
    """

    if current_iteration_time > max_duration_to_iterate or not retry:
        logger.error(log)
        raise AssertionError(log)
    else:
        logger.warning(log)
        logger.info(f"Sleeping for {sleep_duration}s.")
        time.sleep(sleep_duration)
        logger.info(
            f"Retrying, iteration time {current_iteration_time}s / {max_duration_to_iterate}s."
        )


def get_task_cloudtrail_events_by_resource_name(
    region: str,
    target: str,
) -> list[dict]:
    function_name = inspect.stack()[0][3]
    cloudtrail_client = boto3.client("cloudtrail", region_name=region)

    task_id = target.split("/")[-1]

    response = cloudtrail_client.lookup_events(
        LookupAttributes=[{"AttributeKey": "ResourceName", "AttributeValue": target}]
    )

    events = response["Events"]
    logger.info(f"{function_name} - Found CloudTrail events for task {task_id}.")

    return events
