from traceback import format_exc
from logzero import logger

from activities.enums import ParameterMapFailuremode
from vr_runner_lite.experiment import ActivityFailed
from datetime import datetime, timedelta
from typing import List
from botocore.exceptions import ClientError
from activities.ecs.shared import (
    exec_command,
    get_running_tasks_by_family,
    install_stressng_on_task,
    install_tc_on_task,
    handle_test_target_type,
    handle_targets_parameters,
    get_task_arns_by_tag,
    get_task_definition_arns_by_tag,
    attempt_retry_action,
)

import logging
from typing import Literal
import boto3
import datetime
import time

from botocore.exceptions import ClientError
import json
import inspect
from pprint import pformat

from activities.ecs.shared import get_task_arns_by_tag
from activities.ecs.probes import assert_tasks_healthy, assert_tasks_failed

handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

S3_BUCKET_NAME = "experiment-broker-test-rollback-bucket"


def task_kill_process(
    processName: str,
    task_family: str,
    signal: str = "SIGTERM",
    max_duration=600,
    region="us-east-1",
    test_target_type: str = "RANDOM",
):
    kill_process = f"""killall -{signal} {processName}"""
    target_task = get_running_tasks_by_family(
        task_family=task_family, region=region, test_target_type=test_target_type
    )
    try:
        logger.info("Attempting to kill process {} on task {}")
        results = exec_command(
            command=kill_process, task=target_task[0], max_duration=max_duration
        )
        return results
    except Exception as e:
        err = format_exc()
        logger.error(
            f"Killing process on task {target_task[0]} failed with error: {err}"
        )
        raise


def task_stress_network_util(
    task_family: str,
    interface: str = "eth0",
    rate: int = 1000,
    port_type: str = "sport",
    port_number: str = "0",
    test_duration=60,
    max_duration=600,
    region="us-east-1",
    test_target_type: str = "RANDOM",
):
    kill_process = f"""#!/bin/bash
          echo "Injecting high network utilization ..."
          if  [[ "{port_number}" == 0 ]] ; then
            sudo tc qdisc add dev {interface} root tbf rate {rate}kbit latency 50ms burst 1540
            sudo sleep {test_duration}s
            sudo tc qdisc del dev {interface} root
          else  
            sudo tc qdisc add dev {interface} root handle 1: prio priomap 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
            sudo tc qdisc add dev {interface} parent 1:2 handle 20: tbf rate {rate}kbit latency 50ms burst 1540
            sudo tc filter add dev {interface} parent 1:0 protocol ip u32 match ip {port_type} {port_number} 0xffff flowid 1:2
            sudo sleep {test_duration}s
            sudo tc qdisc del dev {interface}root
          fi"""
    target_task = get_running_tasks_by_family(
        task_family=task_family, region=region, test_target_type=test_target_type
    )
    try:
        install_tc_results = install_tc_on_task(
            task=target_task[0], max_duration=max_duration, region=region
        )
        logger.info("Attempting to stress Network Utilization on task {}")
        results = exec_command(
            command=kill_process,
            task=target_task[0],
            max_duration=max_duration,
            region=region,
        )
        return results
    except Exception as e:
        err = format_exc()
        logger.error(
            f"Stressing Network IO on task {target_task[0]} failed with error {err}"
        )
        raise


def task_stress_memory(
    task_family: str,
    workers="10",
    test_percent="10",
    test_duration=60,
    max_duration=600,
    region="us-east-1",
    test_target_type: str = "RANDOM",
):
    kill_process = f"""sudo pgrep stress-ng && echo Another stress-ng command is running, exiting... && exit
          echo Initiating memory stress for { test_duration } seconds, { workers } workers, using { test_percent } of total available memory...
          sudo stress-ng --vm { workers } --vm-bytes { test_percent }% -t { test_duration }s
          echo Finished memory stress."""

    target_task = get_running_tasks_by_family(
        task_family=task_family, region=region, test_target_type=test_target_type
    )
    try:
        install_stressng_results = install_stressng_on_task(
            task=target_task[0], max_duration=max_duration, region=region
        )
        logger.info("Attempting to stress Memory on task {}")
        results = exec_command(
            command=kill_process,
            task=target_task[0],
            max_duration=max_duration,
            region=region,
        )
        return results
    except Exception as e:
        err = format_exc()
        logger.error(
            f"Stressing Memory on task {target_task[0]} failed with error {err}"
        )
        raise


def task_stress_cpu(
    task_family: str,
    test_percent="10",
    test_duration=60,
    max_duration=600,
    region="us-east-1",
    test_target_type: str = "RANDOM",
):
    kill_process = f"""sudo pgrep stress-ng && echo Another stress-ng command is running, exiting... && exit
          echo Initiating CPU stress for { test_duration} seconds...
          sudo stress-ng --cpu { test_percent } --cpu-method matrixprod -t { test_duration}s
          echo Finished CPU stress."""

    target_task = get_running_tasks_by_family(
        task_family=task_family, region=region, test_target_type=test_target_type
    )
    try:
        install_stressng_results = install_stressng_on_task(
            task=target_task[0], max_duration=max_duration, region=region
        )
        logger.info("Attempting to stress CPU on task {}")
        results = exec_command(
            command=kill_process,
            task=target_task[0],
            max_duration=max_duration,
            region=region,
        )
        return results
    except Exception as e:
        err = format_exc()
        logger.error(f"Stressing CPU on task {target_task[0]} failed with error {err}")
        raise


def task_stress_io(
    task_family: str,
    workers="10",
    test_percent="10",
    test_duration=60,
    max_duration=600,
    region="us-east-1",
    test_target_type: str = "RANDOM",
):
    kill_process = f"""sudo pgrep stress-ng && echo Another stress-ng command is running, exiting... && exit
          echo Initiating IO stress for { test_duration} seconds...
          sudo stress-ng --iomix { workers } --iomix-bytes { test_percent }% -t { test_duration}s
          echo Finished IO stress."""

    target_task = get_running_tasks_by_family(
        task_family=task_family, region=region, test_target_type=test_target_type
    )
    try:
        install_stressng_results = install_stressng_on_task(
            task=target_task[0], max_duration=max_duration, region=region
        )
        logger.info("Attempting to stress IO on task {}")
        results = exec_command(
            command=kill_process,
            task=target_task[0],
            max_duration=max_duration,
            region=region,
        )
        return results
    except Exception as e:
        err = format_exc()
        logger.error(f"Stressing IO on task {target_task[0]} failed with error {err}")
        raise


def datetime_handler(x):
    """
    Makes datetime variables JSON serializable. Passed into json.dumps
    """
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")


def halt_tasks_execution(
    region: str,
    cluster_name: str,  # Required parameter, no way to retrieve it with only task_arns (as far as I can tell)
    test_target_type: Literal["ALL", "RANDOM"] = "ALL",
    targets: list[str] = [],
    targets_bucket_name: str = None,
    targets_file_name: str = None,
    reason: str = "Stopped by Experiment Broker.",
    state_bucket_name: str = "experiment-broker-state-bucket",
    state_file_name: str = "halt_tasks_execution.json",
) -> bool:
    """
    Stops tasks in an ecs cluster.
    Waits for tasks to enter the "STOPPED" state.

    Args:
        region (str): AWS region
        cluster_name (str): Name of the ECS cluster
        test_target_type (str): Type of test target
        targets (list[str], Optional): List of task ARNs. Defaults to [].
        target_file_name (str, Optional): S3 state file name. Defaults to None.
        reason (str): Reason for stopping the tasks
        state_file_name (str): S3 state file name

    Returns:
        bool: True if all stop task execution requests were successful, False if exception occured.
    """
    if not targets and (not targets_file_name or not targets_bucket_name):
        error_log = f"{function_name} - Either 'targets' or a 'targets_file_name' and 'targets_bucket_name' must be provided."
        logger.error(error_log)
        raise ValueError(error_log)

    try:
        function_name = inspect.stack()[0][3]

        ecs_client = boto3.client("ecs", region_name=region)
        s3_client = boto3.client("s3", region_name=region)

        targets = handle_targets_parameters(
            region=region,
            targets=targets,
            targets_bucket_name=targets_bucket_name,
            targets_file_name=targets_file_name,
            s3_client=s3_client,
        )

        targets = handle_test_target_type(
            test_target_type=test_target_type, targets=targets
        )

        logger.info(
            f"{function_name} - Stopping tasks: {targets} in cluster: {cluster_name}"
        )

        for target in targets:
            response = ecs_client.stop_task(
                cluster=cluster_name, task=target, reason=reason
            )
            logger.info(f"{function_name} - Task {target} SIGTERM sent.")

        logger.info(f"{function_name} - Waiting for tasks to stop...")

        response = ecs_client.describe_tasks(cluster=cluster_name, tasks=targets)

        rollback = {
            task["taskArn"]: task["stoppingAt"].isoformat()
            for task in response["tasks"]
        }

        logger.info(f"{function_name} - Action Succeeded. All tasks have stopped.")

        logger.info(f"{function_name} - Writing rollback to S3...")
        s3_client.put_object(
            Bucket=state_bucket_name,
            Key=state_file_name,
            Body=json.dumps(rollback, default=datetime_handler),
        )

        logger.info(f"{function_name} - Rollback written to S3.")

    except ClientError as e:
        logger.error(pformat(f"{function_name} - (ClientError): {str(e)}"))
        return False

    except Exception as e:
        logger.error(
            pformat(
                f"{function_name} - (Exception) An unexpected error occurred: {str(e)}"
            )
        )
        return False


def disable_tasks_by_deregister_task_definition(
    region: str,
    test_target_type: Literal["RANDOM", "ALL"] = "ALL",
    targets: list[str] = [],
    state_bucket_name: str = "experiment-broker-state-bucket",
    state_file_name: str = "disable_task_definitions_by_deregister.json",
) -> dict[str, bool]:
    """
    Deregister task definitions by task definition ARN.

    Tags for the task definition are retrieved separately because they are not returned in the deregister_task_definition response.

    Rollback configuration structure:
    {
        "task_definition_arn_1": {...} (task definition details),
        ...
    }



    Args:
        region (str): AWS region
        test_target_type (str): Type of test target
        targets (list[str]): List of task definition ARNs
        state_file_name (str): S3 state file name

    Returns:
        dict[str, bool]: Dictionary of task definition ARNs and success status of their deregistration
    """
    try:
        function_name = inspect.stack()[0][3]
        ecs_client = boto3.client("ecs", region_name=region)
        s3_client = boto3.client("s3", region_name=region)

        logger.info(targets)
        targets = handle_test_target_type(
            test_target_type=test_target_type, targets=targets
        )

        logger.info(
            pformat(f"{function_name} - Deregistering Task Definitions: {targets}")
        )

        deregistration_response = {}
        rollback_config = {}
        for target in targets:
            # tags for the task definition are not returned in the deregister_task_definition response.
            #   Retrieved separately here
            response = ecs_client.list_tags_for_resource(resourceArn=target)
            tags = response["tags"]

            response = ecs_client.deregister_task_definition(taskDefinition=target)

            exclusion_parameters = [
                "taskDefinitionArn",
                "revision",
                "status",
                "requiresAttributes",
                "compatibilities",
                "registeredAt",
                "registeredBy",
            ]

            # If there are failures, log them and set the response to False
            for failure in response.get("failures", []):
                logger.error(
                    pformat(
                        f"{function_name} - Task Definition Deregistration Failure. ARN: {failure['arn']} Reason: {failure['reason']}"
                    )
                )
            # If there are no failures, log the success and set the response to True
            if len(response.get("failures", [])) == 0:
                rollback_config[target] = {}
                for key, value in response["taskDefinition"].items():
                    # dict returned by the deregister_task_definition function contains the information needed to re register
                    #  the task definition. This information is stored in the rollback config
                    if key not in exclusion_parameters:
                        rollback_config[target][key] = value

                # This is where tags are set in the rollback config
                rollback_config[target]["tags"] = tags

                logger.info(
                    pformat(
                        f"{function_name} - Task Definition Deregistration Succeeded. ARN: {response['taskDefinition']['taskDefinitionArn']}"
                    )
                )

                deregistration_response[target] = True
            else:
                deregistration_response[target] = False

        logger.info(pformat(f"{function_name} - Writing rollback config to S3..."))

        # need to use the datetime handler here because getting an error with those values not being JSON serializable.
        response = s3_client.put_object(
            Bucket=state_bucket_name,
            Key=state_file_name,
            Body=json.dumps(rollback_config, default=datetime_handler),
        )

        logger.info(pformat(f"{function_name} - Rollback config written to S3."))

        return deregistration_response
    except Exception as e:
        logger.error(pformat(f"{function_name} - Unknown Error Occurred: {str(e)}"))


def disable_tasks_by_delete_task_definition(
    region: str,
    test_target_type: Literal["RANDOM", "ALL"] = "ALL",
    targets: list[str] = [],
    state_file_name: str = "disable_task_definitions_by_delete.json",
) -> None:
    """
    Delete task definitions by task definition ARN.

    Note that all rollback is handled in the disable_tasks_by_deregister_task_definition function.
    This is because:
        1. To delete a task definition, you need to first deregister it.
        2. The function for "remediating" both deleting and deregistering task definitions is the same (register_task_definition).
        3. The deregister_task_definition function returns the information needed to re-register the task definition.
    Args:
        region (str): AWS region
        test_target_type (str): Type of test target
        targets (list[str]): List of task definition ARNs
        state_file_name (str): S3 state file name

    Returns:
        None
    """
    try:
        function_name = inspect.stack()[0][3]
        ecs_client = boto3.client("ecs", region_name=region)

        targets = handle_test_target_type(
            test_target_type=test_target_type, targets=targets
        )

        logger.info(pformat("Deregistering task definitions..."))
        response = disable_tasks_by_deregister_task_definition(
            region=region,
            test_target_type="ALL",
            targets=targets,
            state_file_name=state_file_name,
        )

        # Sanitize the target list to only include the task definitions that were successfully deregistered
        #   while logging the failures, so that the function can still execute for the successful deregistrations
        for target, success in response.items():
            if success:
                logger.info(
                    pformat(f"Task definition {target} deregistered successfully.")
                )
            else:
                logger.error(
                    pformat(f"Task definition {target} deregistration failed.")
                )
                targets.remove(target)

        logger.info(pformat(f"Deleting task definitions..."))

        if len(targets) > 0:
            response = ecs_client.delete_task_definitions(taskDefinitions=targets)

            for failure in response.get("failures", []):
                logger.error(
                    pformat(
                        f"Task Definition Deletion Failure. ARN: {failure['arn']} Reason: {failure['reason']}"
                    )
                )

            if (len(response.get("failures", [])) == 0) and (len(targets) > 0):
                logger.info(pformat(f"Task Definitions {targets} Deleted."))
            else:
                logger.error(pformat(f"Task Definitions Deletion Failed."))
        else:
            logger.info("No task definitions to delete.")
    except ClientError as e:
        logger.error(pformat(f"{function_name} - {str(e)}"))
    except Exception as e:
        logger.error(
            pformat(
                f"{function_name} - (Exception) An unexpected error occurred: {str(e)}"
            )
        )


def disable_tasks_by_network_inbound(
    region: str,
    cluster: str,
    test_target_type: Literal["RANDOM", "ALL"] = "ALL",
    targets: list[str] = [],
    state_bucket_name: str = "experiment-broker-state-bucket",
    state_file_name: str = "disable_tasks_by_network_inbound.json",
) -> None:
    """
    Disables network inbound rules for tasks.

    The path to the security group is through the network interface because:
        1. Each fargate task has its own network interface
        2. Each network interface is associated with a security group

    So by retrieving a set of security groups from a list of security groups through the network interfaces for the list of tasks,
    we can then revoke the inbound rules for each security group.

    Rollback configuration structure:
    {
        "security_group_id": [{...}, {...}, ...] (IpPermissions)
    }

    Args:
        region (str): AWS region
        cluster (str): ECS cluster name
        test_target_type (str): Type of test target
        targets (list[str]): List of task ARNs
        state_file_name (str): S3 state file name

    Returns:
        None
    """
    ecs_client = boto3.client("ecs", region_name=region)
    ec2_client = boto3.client("ec2", region_name=region)
    s3_client = boto3.client("s3", region_name=region)

    function_name = inspect.stack()[0][3]
    targets = handle_test_target_type(
        test_target_type=test_target_type, targets=targets
    )
    logger.info(
        pformat(f"{function_name} - Getting network interfaces for tasks: {targets}")
    )

    response = ecs_client.describe_tasks(cluster=cluster, tasks=targets)

    target_network_attachment_map = {}
    for task in response["tasks"]:
        for attachment in task["attachments"]:
            if attachment["type"] == "ElasticNetworkInterface":
                target_network_attachment_map[task["taskArn"]] = attachment

    network_interface_id_arr = []

    for target, attachment in target_network_attachment_map.items():
        network_interface_id_arr.append(
            [
                detail["value"]
                for detail in attachment["details"]
                if detail["name"] == "networkInterfaceId"
            ][0]
        )

    logger.info(
        pformat(
            f"{function_name} - Retrieved network interfaces: {network_interface_id_arr}"
        )
    )
    logger.info(
        pformat(
            f"{function_name} - Retrieving security groups from network interfaces..."
        )
    )

    response = ec2_client.describe_network_interfaces(
        NetworkInterfaceIds=network_interface_id_arr
    )

    network_interface_id_security_group_id_map = {}

    for network_interface in response["NetworkInterfaces"]:
        security_group_id = network_interface["Groups"][0]["GroupId"]
        network_interface_id_security_group_id_map[
            network_interface["NetworkInterfaceId"]
        ] = security_group_id

    security_group_ids = list(network_interface_id_security_group_id_map.values())

    logger.info(
        pformat(f"{function_name} - Retrieved security groups {security_group_ids}")
    )

    logger.info(
        pformat(
            f"{function_name} - Retrieving ingress rule configurations for security groups..."
        )
    )

    response = ec2_client.describe_security_groups(GroupIds=security_group_ids)

    ingress_rules = {}
    for security_group in response["SecurityGroups"]:
        ingress_rules[security_group["GroupId"]] = security_group["IpPermissions"]

    logger.info(pformat(f"{function_name} - Saving rollback in s3..."))

    s3_client.put_object(
        Bucket=state_bucket_name, Key=state_file_name, Body=json.dumps(ingress_rules)
    )

    logger.info(pformat(f"{function_name} - Successfully saved rollback in s3."))

    logger.info(pformat(f"{function_name} - Revoking inbound rules..."))

    for security_group_id, ingress_rule in ingress_rules.items():
        if ingress_rule:
            response = ec2_client.revoke_security_group_ingress(
                GroupId=security_group_id, IpPermissions=ingress_rule
            )

            logger.info(
                pformat(
                    f"{function_name} - Revoked inbound rules for security group {security_group_id}."
                )
            )
        else:
            logger.info(
                pformat(
                    f"{function_name} - No inbound rules to revoke for security group {security_group_id}."
                )
            )


def disable_tasks_by_network_outbound(
    region: str,
    cluster: str,
    test_target_type: Literal["RANDOM", "ALL"] = "ALL",  #
    targets: str = [],
    state_bucket_name: str = "experiment-broker-state-bucket",
    state_file_name: str = "disable_tasks_by_network_outbound.json",
) -> None:
    """
    Disables network outbound rules for tasks.

    The path to the security group is through the network interface because:
        1. Each fargate task has its own network interface
        2. Each network interface is associated with a security group

    So by retrieving a set of security groups from a list of security groups, derived from the network interfaces for the list of tasks,
    we can then revoke the outbound rules for each security group.

    Rollback configuration structure:
    {
        "security_group_id": [{...}, {...}, ...] (IpPermissionsEgress)
    }

    Args:
        region (str): AWS region
        cluster (str): ECS cluster name
        test_target_type (str): Type of test target
        targets (list[str]): List of task ARNs
        state_file_name (str): S3 state file name

    Returns:
        None
    """

    ecs_client = boto3.client("ecs", region_name=region)
    ec2_client = boto3.client("ec2", region_name=region)
    s3_client = boto3.client("s3", region_name=region)

    function_name = inspect.stack()[0][3]

    targets = handle_test_target_type(
        test_target_type=test_target_type, targets=targets
    )

    logger.info(
        pformat(f"{function_name} - Getting network interfaces for tasks: {targets}")
    )
    response = ecs_client.describe_tasks(cluster=cluster, tasks=targets)

    target_network_attachment_map = {}
    for task in response["tasks"]:
        for attachment in task["attachments"]:
            if attachment["type"] == "ElasticNetworkInterface":
                target_network_attachment_map[task["taskArn"]] = attachment

    network_interface_id_arr = []

    for target, attachment in target_network_attachment_map.items():
        network_interface_id_arr.append(
            [
                detail["value"]
                for detail in attachment["details"]
                if detail["name"] == "networkInterfaceId"
            ][0]
        )

    logger.info(
        pformat(
            f"{function_name} - Retrieved network interfaces: {network_interface_id_arr}"
        )
    )
    logger.info(
        pformat(
            f"{function_name} - Retrieving security groups from network interfaces..."
        )
    )

    response = ec2_client.describe_network_interfaces(
        NetworkInterfaceIds=network_interface_id_arr
    )

    network_interface_id_security_group_id_map = {}

    for network_interface in response["NetworkInterfaces"]:
        security_group_id = network_interface["Groups"][0]["GroupId"]
        network_interface_id_security_group_id_map[
            network_interface["NetworkInterfaceId"]
        ] = security_group_id

    security_group_ids = list(network_interface_id_security_group_id_map.values())

    logger.info(
        pformat(f"{function_name} - Retrieved security groups {security_group_ids}")
    )

    logger.info(
        pformat(
            f"{function_name} - Retrieving egress rule configurations for security groups..."
        )
    )

    response = ec2_client.describe_security_groups(GroupIds=security_group_ids)

    egress_rules = {}
    for security_group in response["SecurityGroups"]:
        egress_rules[security_group["GroupId"]] = security_group["IpPermissionsEgress"]

    logger.info(pformat(f"{function_name} - Saving rollback in s3..."))

    s3_client.put_object(
        Bucket=state_bucket_name, Key=state_file_name, Body=json.dumps(egress_rules)
    )

    logger.info(pformat(f"{function_name} - Successfully saved rollback in s3."))

    logger.info(pformat(f"{function_name} - Revoking outbound rules..."))

    for security_group_id, egress_rule in egress_rules.items():
        if egress_rule:
            response = ec2_client.revoke_security_group_egress(
                GroupId=security_group_id, IpPermissions=egress_rule
            )

            logger.info(
                pformat(
                    f"{function_name} - Revoked outbound rules for security group {security_group_id}."
                )
            )
        else:
            logger.info(
                pformat(
                    f"{function_name} - No outbound rules to revoke for security group {security_group_id}."
                )
            )


def disable_task_definitions_by_invalid_iam(
    region: str,
    test_target_type: Literal["RANDOM", "ALL"] = "ALL",
    targets: list[str] = [],
    state_bucket_name: str = "experiment-broker-state-bucket",
    state_file_name: str = "disable_task_definitions_by_invalid_iam.json",
) -> None:
    """
    Disables task definitions by invalid IAM roles.

    The IAM roles are retrieved from the task definitions and then the inline and managed policies are revoked.

    Rollback configuration structure:
    {
        "task_role_name": {
            "inline_policies": [{...}, {...}, ...] (PolicyDocument),
            "managed_policies": [{...}, {...}, ...] (PolicyArn),
        },
        ...
    }

    Args:
        region (str): AWS region
        test_target_type (str): Type of test target
        targets (list[str]): List of task definition ARNs
        state_file_name (str): S3 state file name

    Returns:
        None
    """
    ecs_client = boto3.client("ecs", region_name=region)
    iam_client = boto3.client("iam", region_name=region)
    s3_client = boto3.client("s3", region_name=region)

    function_name = inspect.stack()[0][3]

    targets = handle_test_target_type(
        test_target_type=test_target_type, targets=targets
    )

    logger.info(pformat(f"{function_name} - Retrieving Task Role ARNs..."))

    target_task_role_arn_map = {}

    for target in targets:
        response = ecs_client.describe_task_definition(taskDefinition=target)

        task_role_arn = response["taskDefinition"]["taskRoleArn"]
        task_role_name = task_role_arn.split("/")[-1]

        target_task_role_arn_map[target] = task_role_arn

        logger.info(
            pformat(
                f"{function_name} - Succeeded in retrieving Task Role ARN: {task_role_arn} for Task Definition: {target}. Using Task Role Name: {task_role_name}"
            )
        )

    logger.info(pformat(f"{function_name} - Retrieving IAM Role Policies..."))

    rollback = {}
    for target, task_role_arn in target_task_role_arn_map.items():
        response = iam_client.list_role_policies(RoleName=task_role_name)

        # Only has policy names, need to retrieve each policy document
        inline_policy_names = response["PolicyNames"]

        inline_policies = []
        for inline_policy_name in inline_policy_names:
            response = iam_client.get_role_policy(
                RoleName=task_role_name, PolicyName=inline_policy_name
            )
            inline_policies.append({response["PolicyName"]: response["PolicyDocument"]})

        response = iam_client.list_attached_role_policies(RoleName=task_role_name)
        managed_policies = response["AttachedPolicies"]

        rollback[task_role_name] = {
            "inline_policies": inline_policies,
            "managed_policies": managed_policies,
        }

        for inline_policy in inline_policies:
            for policy_name, policy_document in inline_policy.items():
                response = iam_client.delete_role_policy(
                    RoleName=task_role_name, PolicyName=policy_name
                )

                logger.info(
                    pformat(
                        f"{function_name} - Revoked inline policy {policy_name} for IAM Role {task_role_name}."
                    )
                )

        for managed_policy in managed_policies:
            response = iam_client.detach_role_policy(
                RoleName=task_role_name, PolicyArn=managed_policy["PolicyArn"]
            )

            logger.info(
                pformat(
                    f"{function_name} - Revoked managed policy {managed_policy['PolicyName']} with ARN {managed_policy['PolicyArn']} for IAM Role {task_role_name}."
                )
            )

    logger.info(pformat(f"{function_name} - Saving rollback {rollback} in s3..."))

    s3_client.put_object(
        Bucket=state_bucket_name, Key=state_file_name, Body=json.dumps(rollback)
    )

    logger.info(pformat(f"{function_name} - Successfully saved rollback in s3."))


# Priority 5
# def disable_task_by_saturate_task_queue():
#     raise NotImplementedError


def rollback_disable_tasks_by_task_definition(
    region: str,
    state_bucket_name: str = "experiment-broker-state-bucket",
    state_file_name: str = "disable_tasks_by_task_definition.json",
) -> None:
    try:
        function_name = inspect.stack()[0][3]
        ecs_client = boto3.client("ecs", region_name=region)
        s3_client = boto3.client("s3", region_name=region)

        logger.info(pformat(f"{function_name} - Retrieving rollback from S3..."))

        response = s3_client.get_object(Bucket=state_bucket_name, Key=state_file_name)

        if rollback_config := json.loads(response["Body"].read().decode("utf8")):

            for task_definition_arn, task_definition in rollback_config.items():

                if task_definition["deregisteredAt"]:
                    del task_definition["deregisteredAt"]

                response = ecs_client.register_task_definition(**task_definition)
                logger.info(
                    pformat(
                        f"{function_name} - Task Definition Registration Succeeded. ARN: {response['taskDefinition']['taskDefinitionArn']}"
                    )
                )

        else:
            logger.error(
                pformat(f"{function_name} - Rollback config empty. Skipping Rollback.")
            )

    except Exception as e:
        logger.error(pformat(f"{function_name} - {str(e)}"))


def rollback_disable_tasks_by_network_inbound(
    region: str,
    state_bucket_name: str = "experiment-broker-state-bucket",
    state_file_name: str = "disable_task_by_network_inbound.json",
):
    try:
        s3_client = boto3.client("s3", region_name=region)
        ec2_client = boto3.client("ec2", region_name=region)

        function_name = inspect.stack()[0][3]

        logger.info(pformat(f"{function_name} - Retrieving rollback from S3..."))

        response = s3_client.get_object(Bucket=state_bucket_name, Key=state_file_name)
        if rollback_config := json.loads(response["Body"].read().decode("utf8")):
            logger.info(pformat(f"{function_name} - Rollback config retrieved."))

            logger.info(
                pformat(f"{function_name} - Restoring security group ingress...")
            )

            for security_group_id, ingress_rules in rollback_config.items():

                response = ec2_client.authorize_security_group_ingress(
                    GroupId=security_group_id, IpPermissions=ingress_rules
                )

                logger.info(
                    pformat(
                        f"{function_name} - Security group {security_group_id} ingress restored with IpPermissions: {ingress_rules}"
                    )
                )

        else:
            logger.error(
                pformat(f"{function_name} - Rollback config empty. Skipping Rollback.")
            )
            return

    except Exception as e:
        logger.error(pformat(f"{function_name} - {str(e)}"))


def rollback_disable_tasks_by_network_outbound(
    region: str,
    state_bucket_name: str = "experiment-broker-state-bucket",
    state_file_name: str = "disable_task_by_network_outbound.json",
):
    try:
        s3_client = boto3.client("s3", region_name=region)
        ec2_client = boto3.client("ec2", region_name=region)

        function_name = inspect.stack()[0][3]

        logger.info(pformat(f"{function_name} - Retrieving rollback from S3..."))

        response = s3_client.get_object(Bucket=state_bucket_name, Key=state_file_name)
        if rollback_config := json.loads(response["Body"].read().decode("utf8")):
            logger.info(pformat(f"{function_name} - Rollback config retrieved."))

            logger.info(
                pformat(f"{function_name} - Restoring security group egress...")
            )

            for security_group_id, egress_rules in rollback_config.items():

                response = ec2_client.authorize_security_group_egress(
                    GroupId=security_group_id, IpPermissions=egress_rules
                )

                logger.info(
                    pformat(
                        f"{function_name} - Security group {security_group_id} egress restored with IpPermissions: {egress_rules}"
                    )
                )

        else:
            logger.error(
                pformat(f"{function_name} - Rollback config empty. Skipping Rollback.")
            )
            return

    except Exception as e:
        logger.error(pformat(f"{function_name} - {str(e)}"))


def rollback_disable_task_definitions_by_invalid_iam(
    region: str,
    state_bucket_name: str = "experiment-broker-state-bucket",
    state_file_name: str = "disable_task_definitions_by_invalid_iam.json",
):
    try:
        function_name = inspect.stack()[0][3]
        iam_client = boto3.client("iam", region_name=region)
        s3_client = boto3.client("s3", region_name=region)

        logger.info(pformat(f"{function_name} - Retrieving rollback from S3..."))

        response = s3_client.get_object(Bucket=state_bucket_name, Key=state_file_name)

        if rollback_config := json.loads(response["Body"].read().decode("utf8")):
            logger.info(pformat(f"{function_name} - Rollback config retrieved."))

            for task_role_name, policies in rollback_config.items():
                for inline_policy in policies["inline_policies"]:
                    for policy_name, policy_document in inline_policy.items():
                        response = iam_client.put_role_policy(
                            RoleName=task_role_name,
                            PolicyName=policy_name,
                            PolicyDocument=json.dumps(policy_document),
                        )

                        logger.info(
                            pformat(
                                f"{function_name} - Restored inline policy {policy_name} for IAM Role {task_role_name}."
                            )
                        )

                for managed_policy in policies["managed_policies"]:
                    response = iam_client.attach_role_policy(
                        RoleName=task_role_name, PolicyArn=managed_policy["PolicyArn"]
                    )

                    logger.info(
                        pformat(
                            f"{function_name} - Restored managed policy {managed_policy['PolicyName']} with ARN {managed_policy['PolicyArn']} for IAM Role {task_role_name}."
                        )
                    )

        else:
            logger.error(
                pformat(f"{function_name} - Rollback config empty. Skipping Rollback.")
            )

    except Exception as e:
        logger.error(pformat(f"{function_name} - {str(e)}"))


if __name__ == "__main__":

    region = "us-east-1"
    cluster = "experiment-broker-test"
    target_bucket_name = "experiment-broker-test-state-bucket"
    rollback_bucket_name = "experiment-broker-test-rollback-bucket"
    target_file_name = "disable_tasks_execution_target.json"
    rollback_file_name = "disable_tasks_execution_rollback.json"
    tag_key = "Testing"
    tag_value = "True"

    get_task_arns_by_tag(
        region=region,
        cluster_name=cluster,
        tag_key=tag_key,
        tag_value=tag_value,
        task_desired_status="RUNNING",
        task_arn_bucket_name=target_bucket_name,
        task_arn_file_name=target_file_name,
    )

    assert_tasks_healthy(
        region=region,
        cluster_name=cluster,
        targets_bucket_name=target_bucket_name,
        targets_file_name=target_file_name,
        retry=True,
    )

    halt_tasks_execution(
        region=region,
        cluster_name=cluster,
        test_target_type="ALL",
        targets_bucket_name=target_bucket_name,
        targets_file_name=target_file_name,
        state_bucket_name=rollback_bucket_name,
        state_file_name=rollback_file_name,
    )

    assert_tasks_failed(
        region=region,
        cluster_name=cluster,
        targets_bucket_name=target_bucket_name,
        targets_file_name=target_file_name,
        retry=True,
        max_duration_to_iterate=300,
    )
