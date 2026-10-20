import boto3
import logging
import random
import time
import inspect
import json
import botocore.exceptions
import sys
import random

from pprint import pformat
from typing import Literal
from traceback import format_exc
from logzero import logger
from datetime import datetime, timedelta
from vr_runner_lite.experiment import ActivityFailed
from activities.ssm.shared import get_ssm_status
from activities.enums import ParameterMapFailuremode
from botocore.exceptions import ClientError
from random import randint, choice
from typing import Any, Dict, List

handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)


def wait(seconds: int):
    """
    Wait for a specified amount of time. Used to allow external resources time to respond to actions.
    """
    time.sleep(seconds)


# NOTE: Probably will be deleted, saving it for now in case it is needed, but all retries should be handled by probes.
#       Actions need to only execute successfully, all detection of failure or success of an action execution should be handled by probes.
def attempt_retry_action(
    info_log: str,
    current_iteration_time: int,
    max_duration_to_iterate: int,
    sleep_duration: int,
):
    """
    Sleeps if the retry_number is less than max_duration_to_iterate, otherwise raises AssertionError.

    Args:
        info_log (str): Info log message
        current_iteration_time (int): Current iteration time in seconds
        max_duration_to_iterate (int): Maximum duration to attempt iterations in seconds
        sleep_duration (int): sleep duration time in seconds

    Raises:
        AssertionError if current_iteration_time is greater than max_duration_to_iterate
    """
    logger.info(info_log)
    if current_iteration_time > max_duration_to_iterate:
        raise Exception(info_log)
    else:
        logger.info(f"Sleeping for {sleep_duration}s.")
        time.sleep(sleep_duration)
        logger.info(
            f"Retrying, iteration time {current_iteration_time + sleep_duration}s / {max_duration_to_iterate}s."
        )


def attempt_retry_probe(
    warning_log: str,
    retry: bool,
    current_iteration_time: int,
    max_duration_to_iterate: int,
    sleep_duration: int,
):
    """
    Sleeps if retry is True and the retry_number is less than max_duration_to_iterate, otherwise raises AssertionError.


    Args:
        warning_log (str): Warning log message
        retry (bool): Retry flag
        current_iteration_time (int): Current iteration time in seconds
        max_duration_to_iterate (int): Maximum duration to attempt iterations in seconds
        sleep_duration (int): sleep duration time in seconds

    Raises:
        AssertionError if retry is False or current_iteration_time is greater than max_duration_to_iterate
    """
    logger.warning(warning_log)
    if current_iteration_time > max_duration_to_iterate or not retry:
        raise AssertionError(warning_log)
    else:
        logger.info(f"Sleeping for {sleep_duration}s.")
        time.sleep(sleep_duration)
        logger.info(
            f"Retrying, iteration time {current_iteration_time}s / {max_duration_to_iterate}s."
        )


def handle_targets_parameters(
    region: str,
    targets: list[str],
    targets_bucket_name: str,
    targets_file_name: str,
    s3_client: any = None,
) -> str:
    """
    Handle the targets parameters. Returns targets if targets are specified. Otherwise, retrieves the targets from the S3 bucket.

    Args:
        region (str): AWS region
        targets (list[str]): List of targets
        targets_bucket_name (str): Bucket name
        targets_file_name (str): File name
        s3_client (any, optional): S3 client. Defaults to None.

    Returns:
        list[str]: List of targets
    """
    if targets:
        return targets

    s3_client = (
        boto3.client("s3", region_name=region) if s3_client is None else s3_client
    )
    response = s3_client.get_object(Bucket=targets_bucket_name, Key=targets_file_name)

    return json.loads(response["Body"].read().decode("utf8"))


def get_task_arns_by_tag(
    region: str,
    cluster_name: str,
    tag_key: str,
    tag_value: str,
    task_desired_status: Literal["RUNNING", "STOPPED", "ALL"] = "ALL",
    task_arn_bucket_name: str = None,
    task_arn_file_name: str = None,
) -> list[str]:
    """
    Get the task ARNs by tag.

    By default, list_tasks only returns tasks with desired status of RUNNING. The set of options provided by boto3 are:
    - RUNNING: The desired task status is running.
    - STOPPED: The desired task status is stopped.
    task_status of ALL will return all tasks regardless of status by querying for both desired statuses.


    Args:
        cluster_name (str): Name of the ECS cluster
        region (str): AWS region
        tag_key (str): Tag key
        tag_value (str): Tag value
        task_desired_status (Literal["RUNNING", "STOPPED", "ALL"], optional) the desired task status to filter by. Defaults to every status.
        task_arn_file_name (str, optional): Target file name, which will contain the ARN. Defaults to None.

    Returns:
        list[str]: List of task ARNs
    """
    ecs_client = boto3.client("ecs", region)
    ecs_tasks_list: list[str] = []

    if task_desired_status not in ["RUNNING", "STOPPED", "ALL"]:
        raise ValueError(
            f"Invalid task_desired_status: {task_desired_status}. Needs to be 'RUNNING', 'STOPPED', or 'ALL'"
        )

    desired_statuses = (
        ["RUNNING", "STOPPED"]
        if task_desired_status == "ALL"
        else [task_desired_status]
    )
    for status in desired_statuses:
        resp = ecs_client.list_tasks(cluster=cluster_name, desiredStatus=status)[
            "taskArns"
        ]
        ecs_tasks_list.extend(resp)
    ecs_tasks = ecs_client.describe_tasks(
        cluster=cluster_name, tasks=ecs_tasks_list, include=["TAGS"]
    )
    task_ids = []
    for task in ecs_tasks["tasks"]:
        if task["tags"]:
            for tag in task["tags"]:
                if tag["key"] == tag_key and tag["value"] == tag_value:
                    task_ids.append(task["taskArn"])
    if not task_ids:
        logger.info(
            f'Cluster {cluster_name} does not contain any tasks with tag "{tag_key}:{tag_value}"'
        )
    else:
        logger.info(pformat(f"Retrieved Task ARNs: {task_ids}"))

    if task_arn_file_name and task_arn_bucket_name:
        s3_client = boto3.client("s3", region_name=region)
        s3_client.put_object(
            Bucket=task_arn_bucket_name,
            Key=task_arn_file_name,
            Body=json.dumps(task_ids),
        )

    return task_ids


def get_task_definition_arns_by_tag(region: str, tag_key: str, tag_value: str):
    ecs_client = boto3.client("ecs", region)
    ecs_task_definitions_list = ecs_client.list_task_definitions(
        status="ACTIVE", sort="DESC"
    )
    task_definition_arns = []
    for task_definition_arn in ecs_task_definitions_list["taskDefinitionArns"]:
        task_definition_detail = ecs_client.list_tags_for_resource(
            resourceArn=task_definition_arn
        )
        if task_definition_detail["tags"]:
            for tag in task_definition_detail["tags"]:
                if tag["key"] == tag_key and tag["value"] == tag_value:
                    task_definition_arns.append(task_definition_arn)
    if not task_definition_arns:
        logger.info(
            f"Region {region} does not contain any task definitions with tag '{tag_key}:{tag_value}'"
        )
    else:
        logger.info(pformat(f"Retrieved Task Definition ARNs: {task_definition_arns}"))
    return task_definition_arns


def get_task_statuses_by_arn(
    region: str,
    cluster_name: str,
    targets: list[str],
    last_status: str = None,
    desired_status: str = None,
) -> dict[str, bool]:
    """
    Get the task status by ARN.

    Args:
        region (str): AWS region
        cluster_name (str): Name of the ECS cluster
        targets (list[str]): List of task ARNs
        last_status (str, optional): Last status. Defaults to None.
        desired_status (str, optional): Desired status. Defaults to None.


    Returns:
        dict[str, bool]: Task status, bool True if the response status matches the parameter status
    """
    try:
        function_name = inspect.stack()[0][3]

        ecs_client = boto3.client("ecs", region)
        response = ecs_client.describe_tasks(cluster=cluster_name, tasks=targets)

        status = {}
        for task in response["tasks"]:
            status[task["taskArn"]] = {}
            if last_status:
                status[task["taskArn"]]["last_status"] = (
                    task["lastStatus"] == last_status
                )
            if desired_status:
                status[task["taskArn"]]["desired_status"] = (
                    task["desiredStatus"] == desired_status
                )
        return status
    except Exception as e:
        logger.error(f"{function_name} - Unexpected Error: " + str(e))
        return {
            task["taskArn"]: {"last_status": None, "desired_status": None}
            for task in targets
        }


def handle_test_target_type(test_target_type: str, targets: list[str]) -> list[str]:
    """
    Handle the test_target_type and return the appropriate list of targets

    Args:
        test_target_type (str): Type of test target
        targets (list[str]): List of targets

    Returns:
        list[str]: List of targets
    """
    if test_target_type not in ["ALL", "RANDOM"]:
        raise ValueError(
            f"Invalid test_target_type: {test_target_type}. Needs to be 'ALL' or 'RANDOM'"
        )

    if test_target_type == "ALL":
        return targets
    elif test_target_type == "RANDOM":
        return random.sample(targets, random.randint(1, len(targets)))


def get_running_tasks_by_family(task_family: str, region: str, test_target_type: str):
    ecs_client = boto3.client("ecs", region=region)
    tasks = ecs_client.list_tasks(family=task_family, desiredStatus="RUNNING")[
        "taskArns"
    ]
    if test_target_type == "RANDOM":
        return [random.choice(tasks)]
    elif test_target_type == "ALL":
        return
    else:
        logger.error(f"Test Type {test_target_type}")
        raise NotImplementedError(f"Test Type not supported: {test_target_type}")


def install_stressng_on_task(
    task: str, max_duration: int = 600, region: str = "us-east-1"
):
    command = """#!/bin/bash
            if [[ "$( which stress-ng 2>/dev/null )" ]] ; then echo Dependency is already installed. ; exit ; fi
            echo "Installing required dependencies"
            if [ -f  "/etc/system-release" ] ; then
              if sudo cat /etc/system-release | grep -i 'Amazon Linux' ; then
                sudo amazon-linux-extras install testing
                sudo yum -y install stress-ng
              else
                echo "There was a problem installing dependencies."
                exit 1
              fi
            elif sudo cat /etc/issue | grep -i Ubuntu ; then
              sudo apt-get update -y
              sudo DEBIAN_FRONTEND=noninteractive sudo apt-get install -y stress-ng
            else
              echo "There was a problem installing dependencies."
              exit 1
            fi"""
    try:
        logger.info(f"Attempting to install Stressng on task {task}")
        results = exec_command(command=command, task=task, max_duration=max_duration)
        return results
    except Exception as e:
        err = format_exc()
        logger.error(f"Installing StressNG on task failed with error: {err}")
        raise


def install_tc_on_task(task: str, max_duration: int = 600, region: str = "us-east-1"):
    command = """#!/bin/bash
            if [[ "$( which tc 2>/dev/null )" ]] ; then echo Dependency is already installed. ; exit ; fi
            echo "Installing required dependencies"
            if [ -f  "/etc/system-release" ] ; then
              if sudo cat /etc/system-release | grep -i 'Amazon Linux' ; then
                sudo amazon-linux-extras install testing
                sudo yum -y install tc
              else
                echo "There was a problem installing dependencies."
                exit 1
              fi
            elif sudo cat /etc/issue | grep -i Ubuntu ; then
              sudo apt-get update -y
              sudo DEBIAN_FRONTEND=noninteractive sudo apt-get install -y iproute2
            else
              echo "There was a problem installing dependencies."
              exit 1
            fi"""
    try:
        logger.info(f"Attempting to install tc on task {task}")
        results = exec_command(command=command, task=task, max_duration=max_duration)
        return results
    except Exception as e:
        err = format_exc()
        logger.error(f"Installing tc on task failed with error: {err}")
        raise


def exec_command(
    command: str,
    task: str,
    cluster: str = None,
    container: str = None,
    max_duration: int = 600,
    region: str = "us-east-1",
):
    """Handler to manage running commands against ECS tasks and getting their results"""
    results: list = []

    ecs_client = boto3.client("ecs", region=region)
    try:
        run_id = ecs_client.execute_command(
            cluster=cluster,
            container=container,
            command=command,
            task=task,
            interactive=False,
        )
        session = boto3.Session()
        ssm_client = session.client("ssm", region)
        try:
            run_results = get_ssm_status(
                ssm=ssm_client,
                command_id=run_id["session"]["sessionId"],
                max_duration=max_duration,
            )
        except TimeoutError:
            raise ActivityFailed(
                f"Command failed to run: Max duration of {max_duration} seconds exceeded"
            )
        failed = [x for x in run_results if x["status"] != "Success"]
        if failed:
            for failure in failed:
                output = ";".join([x["output"] for x in failure["output"]])
                logger.error(
                    f"{failed['instanceid']} failed in ssm execution with output: {output}"
                )
                results.append((task, "failed", run_results))
            results.append((task, "success", run_results))
    except Exception as e:
        logger.error(e)
        err = format_exc()
        try:
            results.append((task, "failed", run_results))
        except NameError:
            results.append((task, "failed", err))
    return results
