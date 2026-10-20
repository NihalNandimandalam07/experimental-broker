import boto3
import logging
import inspect
import json
from pprint import pformat
from botocore.exceptions import ClientError
from activities.ecs.shared import (
    get_task_statuses_by_arn,
    attempt_retry_probe,
    handle_targets_parameters,
)


handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)


def assert_tasks_healthy(
    region: str,
    cluster_name: str,
    targets: list[str] = [],
    targets_bucket_name: str = None,
    targets_file_name: str = None,
    retry: bool = False,
    max_duration_to_iterate: int = 60,
    sleep_duration: int = 15,
) -> bool:
    """
    Assert that a task is healthy.
    Task is defined as "healthy" if both the LastStatus and DesiredStatus is running.
    Requires that either a target or a target_file_name is provided. If both are provided, the target will be used.

    Args:
        region (str): AWS region
        cluster_name (str): Name of the ECS cluster
        targets (list[str], optional): Task ARNs. Defaults to [].
        targets_file_name (str, optional): File name where the task ARNs is stored. Defaults to None.
        retry (bool, optional): Retry assertion. Defaults to False.
        max_duration_to_iterate (int, optional): Maximum duration to iterate. Defaults to 60.
        sleep_duration (int, optional): Sleep duration between iterations. Defaults to 15.
    Returns:
        bool: True if the task is healthy, False otherwise
    """
    function_name = inspect.stack()[0][3]

    if not targets and not targets_file_name:
        error_log = f"{function_name} - Either 'targets' or a 'target_file_name' must be provided."
        logger.error(error_log)
        raise ValueError(error_log)

    try:
        targets = handle_targets_parameters(
            region=region,
            targets=targets,
            targets_bucket_name=targets_bucket_name,
            targets_file_name=targets_file_name,
        )

        logger.info(f"{function_name} - Asserting Tasks {targets} healthy.")

        current_iteration_time = 0
        while True:
            task_status_response: dict[str : dict[str:str]] = get_task_statuses_by_arn(
                region=region,
                cluster_name=cluster_name,
                targets=targets,
                last_status="RUNNING",
                desired_status="RUNNING",
            )

            # Returns false if the desired status is not RUNNING, meaning the task cannot be healthy

            failed_last_status_responses = {
                task_arn: task_statuses["last_status"]
                for task_arn, task_statuses in task_status_response.items()
                if task_statuses["last_status"] != True
            }

            failed_desired_status_responses = {
                task_arn: task_statuses["desired_status"]
                for task_arn, task_statuses in task_status_response.items()
                if task_statuses["desired_status"] != True
            }

            if failed_desired_status_responses:
                error_log = f"{function_name} - Failed asserting Tasks health, Desired Status not 'RUNNING': {failed_desired_status_responses}"
                raise AssertionError(error_log)

            # Will retry if the last task status is not RUNNING, as it may take a while for a new task to provision
            if failed_last_status_responses:
                warning_log = f"{function_name} - Failed asserting Tasks health, Last Status not 'RUNNING': {failed_last_status_responses}"
                attempt_retry_probe(
                    warning_log=warning_log,
                    retry=retry,
                    current_iteration_time=current_iteration_time,
                    max_duration_to_iterate=max_duration_to_iterate,
                    sleep_duration=sleep_duration,
                )
                current_iteration_time += sleep_duration
            else:
                break
        logger.info(f"{function_name} - Succeeded asserting Tasks {targets} healthy.")
        return True
    except AssertionError as e:
        logger.error(f"{function_name} - (AssertionError) " + str(e))
        return False
    except Exception as e:
        logger.error(f"{function_name} - (Unexpected Exception) " + str(e))
        return False


def assert_tasks_failed(
    region: str,
    cluster_name: str,
    targets: list[str] = [],
    targets_bucket_name: str = None,
    targets_file_name: str = None,
    retry: bool = False,
    max_duration_to_iterate: int = 60,
    sleep_duration: int = 15,
):
    """
    Assert that a task has failed.
    Task is defined as "failed" if the DesiredStatus or LastStatus is STOPPED.
    Requires that either a target or a target_file_name is provided. If both are provided, the target will be used.

    Args:
        region (str): AWS region
        cluster_name (str): Name of the ECS cluster
        targets (list[str], optional): Task ARNs. Defaults to [].
        targets_file_name (str, optional): File name where the task ARNs is stored. Defaults to None.
        retry (bool, optional): Retry assertion. Defaults to False.
        max_duration_to_iterate (int, optional): Maximum duration to iterate. Defaults to 60.
        sleep_duration (int, optional): Sleep duration between iterations. Defaults to 15.

    Returns:
        bool: True if the task has failed, False otherwise.
    """

    function_name = inspect.stack()[0][3]

    if not targets and not targets_file_name:
        error_log = f"{function_name} - Either 'targets' or a 'target_file_name' must be provided."
        logger.error(error_log)
        raise ValueError(error_log)

    try:
        targets = handle_targets_parameters(
            region=region,
            targets=targets,
            targets_bucket_name=targets_bucket_name,
            targets_file_name=targets_file_name,
        )

        logger.info(f"{function_name} - Asserting Tasks {targets} failure.")

        current_iteration_time = 0
        while True:
            task_status_response = get_task_statuses_by_arn(
                region=region,
                cluster_name=cluster_name,
                targets=targets,
                last_status="STOPPED",
            )

            failed_last_status_responses = {
                task_arn: task_statuses["last_status"]
                for task_arn, task_statuses in task_status_response.items()
                if task_statuses["last_status"] != True
            }

            if failed_last_status_responses:
                warning_log = f"{function_name} - Failed asserting Tasks failure, Last Statuses not 'STOPPED': {failed_last_status_responses}."
                attempt_retry_probe(
                    warning_log=warning_log,
                    retry=retry,
                    current_iteration_time=current_iteration_time,
                    max_duration_to_iterate=max_duration_to_iterate,
                    sleep_duration=sleep_duration,
                )
                current_iteration_time += sleep_duration
            else:
                break
        logger.info(f"{function_name} - Succeeded asserting Tasks {targets} failure.")
        return True
    except AssertionError as e:
        logger.error(f"{function_name} - (AssertionError) " + str(e))
        return False
    except Exception as e:
        logger.error(f"{function_name} - (Unexpected Exception) " + str(e))
        return False


def assert_task_replaced(
    region: str,
    cluster_name: str,
    target: str,
    tag_key: str = None,
    tag_value: str = None,
    retry: bool = False,
    max_duration_to_iterate: int = 60,
    sleep_duration: int = 15,
):
    """
    Assert that a task has been replaced.

    Takes the task family from the provided task ARN in the 'target' parameter.
    Checks that the target is stopped.
    Asserts that a task in the same family was started after the termination of the target task.
    If there are, and they were started after the stop time of the target task, then the target task has been replaced.
    Optionally, if a tag_key and tag_value are provided, only tasks with that tag key value pair will be considered.

    Args:
        region (str): AWS region
        cluster_name (str): Name of the ECS cluster
        target (str): Task ARN
        tag_key (str, optional): Tag key. Defaults to None.
        tag_value (str, optional): Tag value. Defaults to None.
        retry (bool, optional): Retry assertion. Defaults to False.
        max_duration_to_iterate (int, optional): Maximum number of retries. Defaults to 3.
        sleep_duration (int, optional): sleep_duration time between retries. Defaults to 15.

    Raises:
        AssertionError: If the task has not been replaced after the maximum number of retries.
    """
    function_name = inspect.stack()[0][3]

    ecs_client = boto3.client("ecs", region_name=region)

    target_task = ecs_client.describe_tasks(cluster=cluster_name, tasks=[target])[
        "tasks"
    ][0]

    current_iteration_time = 0
    while True:
        response = ecs_client.list_tasks(
            cluster=cluster_name,
            family=target_task["taskDefinitionArn"].split(":")[-2].split("/")[-1],
            desiredStatus="RUNNING",
        )

        # If no valid tasks are running, attempt retries until there are
        if response["taskArns"]:

            describe_resp = ecs_client.describe_tasks(
                cluster=cluster_name, tasks=response["taskArns"], include=["TAGS"]
            )
            tasks = describe_resp["tasks"]
            current_running_tasks = []
            # if filtering by tag, only consider tasks with the tag key value pair
            if tag_key and tag_value:
                for task in tasks:
                    if any(
                        tag["key"] == tag_key and tag["value"] == tag_value
                        for tag in task["tags"]
                    ):
                        current_running_tasks.append(task)
            else:
                current_running_tasks = tasks

            # Filter by tasks that started after the target task stopped

            current_running_tasks = [
                task
                for task in current_running_tasks
                if task["createdAt"] > target_task["stoppedAt"]
            ]

            if not current_running_tasks:
                error_log = (
                    f"{function_name} - Failed asserting Task {target} replacement."
                )
                attempt_retry_probe(
                    error_log=error_log,
                    retry=retry,
                    current_iteration_time=current_iteration_time,
                    max_duration_to_iterate=max_duration_to_iterate,
                    sleep_duration=sleep_duration,
                )
                current_iteration_time += sleep_duration
            else:
                logger.info(
                    f"{function_name} - Succeeded asserting Task {target} replacement."
                )
                break
        else:
            attempt_retry_probe(
                error_log=f"{function_name} - No valid tasks running.",
                retry=retry,
                current_iteration_time=current_iteration_time,
                max_duration_to_iterate=max_duration_to_iterate,
                sleep_duration=sleep_duration,
            )
            current_iteration_time += sleep_duration


# NOTE: If this is something we want to do, we need to figure out how to remove
#       IAM permissions from tasks already running. From what I've read, it seems
#       like tasks keep their permissions until they are stopped and restarted (?)
# def assert_task_invalid_iam():
#     raise NotImplementedError


def assert_task_definition_invalid_iam(
    region: str,
    target: str,
    retry: bool = False,
    max_duration_to_iterate: int = 30,
    sleep_duration: int = 15,
):
    """
    Assert that a task definition has invalid IAM permissions.

    Args:
        region (str): AWS region
        target (str): Task Definition ARN
        retry (bool, optional): Retry assertion. Defaults to False.
        max_duration_to_iterate (int, optional): Maximum number of retries. Defaults to 3.
        sleep_duration (int, optional): Sleep duration between retries. Defaults to 30.

    Raises:
        AssertionError: If the task definition has not been replaced after the maximum number of retries.
    """

    function_name = inspect.stack()[0][3]

    ecs_client = boto3.client("ecs", region_name=region)
    iam_client = boto3.client("iam", region_name=region)

    current_iteration_time = 0
    while True:
        task_definition = ecs_client.describe_task_definition(taskDefinition=target)
        role_name = task_definition["taskDefinition"]["taskRoleArn"].split("/")[-1]

        response_inline = iam_client.list_role_policies(RoleName=role_name)
        response_managed = iam_client.list_attached_role_policies(RoleName=role_name)

        if response_managed["AttachedPolicies"] or response_inline["PolicyNames"]:
            error_log = f"{function_name} - Failed asserting Task Definition {target} invalid IAM."
            attempt_retry_probe(
                error_log=error_log,
                retry=retry,
                current_iteration_time=current_iteration_time,
                max_duration_to_iterate=max_duration_to_iterate,
                sleep_duration=sleep_duration,
            )
            current_iteration_time += sleep_duration
        else:
            logger.info(
                pformat(
                    f"{function_name} - Succeeded asserting Task Definition {target} invalid IAM."
                )
            )
            break


# NOTE: See assert_task_invalid_iam note
# def assert_task_remediated_iam():
#     raise NotImplementedError


def assert_task_definition_remediated_iam(
    region: str,
    target: str,
    rollback_bucket_name: str,
    rollback_file_name: str,
    retry: bool = False,
    max_duration_to_iterate: int = 30,
    sleep_duration: int = 15,
):
    function_name = inspect.stack()[0][3]

    s3_client = boto3.client("s3", region_name=region)
    ecs_client = boto3.client("ecs", region_name=region)
    iam_client = boto3.client("iam", region_name=region)

    rollback_file = s3_client.get_object(
        Bucket=rollback_bucket_name, Key=rollback_file_name
    )
    if rollback_config := json.loads(rollback_file["Body"].read().decode("utf-8")):

        task_definition = ecs_client.describe_task_definition(taskDefinition=target)[
            "taskDefinition"
        ]

        task_role_names = [task_role_name for task_role_name in rollback_config.keys()]
        target_task_role_name = task_definition["taskRoleArn"].split("/")[-1]

        if target_task_role_name in task_role_names:
            logger.info(
                f"{function_name} - Role {target_task_role_name} is attached to Task Definition {target}."
            )
        else:
            error_log = f"{function_name} - Role {target_task_role_name} is not attached to Task Definition {target}."
            logger.error(error_log)
            raise AssertionError(error_log)

        policies = rollback_config[target_task_role_name]

        current_iteration_time = 0
        while True:
            inline_policies = iam_client.list_role_policies(
                RoleName=target_task_role_name
            )["PolicyNames"]

            target_inline_policy_names = [
                list(policy.keys())[0] for policy in policies["inline_policies"]
            ]

            policies_not_attached = [
                policy
                for policy in target_inline_policy_names
                if policy not in inline_policies
            ]

            if policies_not_attached:
                error_log = f"{function_name} - Inline policies {policies_not_attached} are not attached to role {target_task_role_name}."

                attempt_retry_probe(
                    error_log=error_log,
                    retry=retry,
                    current_iteration_time=current_iteration_time,
                    max_duration_to_iterate=max_duration_to_iterate,
                    sleep_duration=sleep_duration,
                )
                current_iteration_time += sleep_duration
                continue
            else:
                logger.info(
                    pformat(
                        f"{function_name} - All inline policies in rollback are attached to role {target_task_role_name}."
                    )
                )
                break

        current_iteration_time = 0
        while True:
            # Check if the managed policies are attached to the role
            attached_policies = iam_client.list_attached_role_policies(
                RoleName=target_task_role_name
            )["AttachedPolicies"]
            attached_policy_names = [
                policy["PolicyName"] for policy in attached_policies
            ]

            policies_not_attached = [
                policy["PolicyName"]
                for policy in policies["managed_policies"]
                if policy["PolicyName"] not in attached_policy_names
            ]

            if policies_not_attached:
                error_log = f"{function_name} - Managed policies {policies_not_attached} are not attached to role {target_task_role_name}."

                attempt_retry_probe(
                    error_log=error_log,
                    retry=retry,
                    current_iteration_time=current_iteration_time,
                    max_duration_to_iterate=max_duration_to_iterate,
                    sleep_duration=sleep_duration,
                )
                current_iteration_time += sleep_duration
                continue
            else:
                logger.info(
                    f"{function_name} - All managed policies in rollback are attached to role {target_task_role_name}."
                )
                break
    else:
        error_log = pformat(
            f"{function_name} - Rollback config empty. Skipping Rollback."
        )
        logger.error(error_log)
        raise AssertionError(error_log)


def assert_tasks_disabled_network_inbound(
    region: str,
    cluster_name: str,
    targets: list[str],
    retry: bool = False,
    max_duration_to_iterate: int = 30,
    sleep_duration: int = 15,
):
    function_name = inspect.stack()[0][3]

    ecs_client = boto3.client("ecs", region_name=region)
    ec2_client = boto3.client("ec2", region_name=region)

    response = ecs_client.describe_tasks(cluster=cluster_name, tasks=targets)

    network_interface_error = []
    network_interface_ids = []
    for task in response["tasks"]:
        network_interface_id = None
        for attachment in task["attachments"]:
            if attachment["type"] == "ElasticNetworkInterface":
                network_interface_id = [
                    details["value"]
                    for details in attachment["details"]
                    if details["name"] == "networkInterfaceId"
                ][0]

        if network_interface_id is None:
            network_interface_error.append(task["taskArn"])
        else:
            network_interface_ids.append(network_interface_id)
    if network_interface_error:
        error_log = pformat(
            f"{function_name} - Tasks {network_interface_error} do not have network interfaces attached."
        )
        logger.error(error_log)
        raise AssertionError(error_log)

    response = ec2_client.describe_network_interfaces(
        NetworkInterfaceIds=network_interface_ids
    )
    security_groups = []
    for network_interface in response["NetworkInterfaces"]:
        security_groups.extend(network_interface["Groups"])

    current_iteration_time = 0
    while True:
        response = ec2_client.describe_security_groups(
            GroupIds=list(set([group["GroupId"] for group in security_groups]))
        )
        security_group_error = []
        for security_group in response["SecurityGroups"]:
            if len(security_group["IpPermissions"]) > 0:
                security_group_error.append(security_group["GroupId"])

        if security_group_error:
            error_log = pformat(
                f"{function_name} - Security Groups {security_group_error} have inbound rules."
            )
            attempt_retry_probe(
                error_log=error_log,
                retry=retry,
                current_iteration_time=current_iteration_time,
                max_duration_to_iterate=max_duration_to_iterate,
                sleep_duration=sleep_duration,
            )
            current_iteration_time += sleep_duration
        else:
            logger.info(
                pformat(
                    f"{function_name} - Succeeded asserting Task network inbound disabled."
                )
            )
            break


def assert_tasks_disabled_network_outbound(
    region: str,
    cluster_name: str,
    targets: list[str],
    retry: bool = False,
    max_duration_to_iterate: int = 30,
    sleep_duration: int = 15,
):
    function_name = inspect.stack()[0][3]

    ecs_client = boto3.client("ecs", region_name=region)
    ec2_client = boto3.client("ec2", region_name=region)

    response = ecs_client.describe_tasks(cluster=cluster_name, tasks=targets)

    network_interface_error = []
    network_interface_ids = []
    for task in response["tasks"]:
        network_interface_id = None
        for attachment in task["attachments"]:
            if attachment["type"] == "ElasticNetworkInterface":
                network_interface_id = [
                    details["value"]
                    for details in attachment["details"]
                    if details["name"] == "networkInterfaceId"
                ][0]

        if network_interface_id is None:
            network_interface_error.append(task["taskArn"])
        else:
            network_interface_ids.append(network_interface_id)
    if network_interface_error:
        error_log = pformat(
            f"{function_name} - Tasks {network_interface_error} do not have network interfaces attached."
        )
        logger.error(error_log)
        raise AssertionError(error_log)

    response = ec2_client.describe_network_interfaces(
        NetworkInterfaceIds=network_interface_ids
    )

    security_groups = []
    for network_interface in response["NetworkInterfaces"]:
        security_groups.extend(network_interface["Groups"])

    current_iteration_time = 0
    while True:
        response = ec2_client.describe_security_groups(
            GroupIds=list(set([group["GroupId"] for group in security_groups]))
        )
        security_group_error = []
        for security_group in response["SecurityGroups"]:
            if len(security_group["IpPermissionsEgress"]) > 0:
                security_group_error.append(security_group["GroupId"])

        if security_group_error:
            error_log = pformat(
                f"{function_name} - Security Groups {security_group_error} have outbound rules."
            )
            attempt_retry_probe(
                error_log=error_log,
                retry=retry,
                current_iteration_time=current_iteration_time,
                max_duration_to_iterate=max_duration_to_iterate,
                sleep_duration=sleep_duration,
            )
            current_iteration_time += sleep_duration
        else:
            logger.info(
                pformat(
                    f"{function_name} - Succeeded asserting Task network inbound disabled."
                )
            )
            break


def assert_tasks_remediated_network_inbound(
    region: str,
    rollback_bucket_name: str,
    rollback_file_name: str,
    retry: bool = False,
    max_duration_to_iterate: int = 30,
    sleep_duration: int = 15,
):
    function_name = inspect.stack()[0][3]

    ec2_client = boto3.client("ec2", region_name=region)
    s3_client = boto3.client("s3", region_name=region)

    rollback_file = s3_client.get_object(
        Bucket=rollback_bucket_name, Key=rollback_file_name
    )
    if rollback_config := json.loads(rollback_file["Body"].read().decode("utf-8")):

        group_ids = rollback_config.keys()

        current_iteration_time = 0
        while True:
            response = ec2_client.describe_security_groups(GroupIds=list(group_ids))
            existing_security_groups = response["SecurityGroups"]

            remediation_error = []
            for group_id, ip_permissions in rollback_config.items():
                if sorted(str(i) for i in ip_permissions) != sorted(
                    str(i)
                    for i in [
                        security_group["IpPermissions"]
                        for security_group in existing_security_groups
                        if security_group["GroupId"] == group_id
                    ][0]
                ):
                    remediation_error.append(group_id)

            if remediation_error:
                error_log = f"{function_name} - Failed asserting Task network inbound remediation for security groups {remediation_error}."

                attempt_retry_probe(
                    error_log=error_log,
                    retry=retry,
                    current_iteration_time=current_iteration_time,
                    max_duration_to_iterate=max_duration_to_iterate,
                    sleep_duration=sleep_duration,
                )
                current_iteration_time += sleep_duration
            else:
                logger.info(
                    "Succeeded asserting network inbound remediated from rollback."
                )
                break
    else:
        error_log = f"{function_name} - Rollback config empty."
        logger.error(error_log)
        raise AssertionError(error_log)


def assert_tasks_remediated_network_outbound(
    region: str,
    rollback_bucket_name: str,
    rollback_file_name: str,
    retry: bool = False,
    max_duration_to_iterate: int = 30,
    sleep_duration: int = 15,
):
    function_name = inspect.stack()[0][3]

    ec2_client = boto3.client("ec2", region_name=region)
    s3_client = boto3.client("s3", region_name=region)

    rollback_file = s3_client.get_object(
        Bucket=rollback_bucket_name, Key=rollback_file_name
    )
    if rollback_config := json.loads(rollback_file["Body"].read().decode("utf-8")):
        group_ids = rollback_config.keys()

        current_iteration_time = 0
        while True:
            response = ec2_client.describe_security_groups(GroupIds=list(group_ids))
            existing_security_groups = response["SecurityGroups"]

            remediation_error = []
            for group_id, ip_permissions in rollback_config.items():
                if sorted(str(i) for i in ip_permissions) != sorted(
                    str(i)
                    for i in [
                        security_group["IpPermissionsEgress"]
                        for security_group in existing_security_groups
                        if security_group["GroupId"] == group_id
                    ][0]
                ):
                    remediation_error.append(group_id)

            if remediation_error:
                error_log = f"{function_name} - Failed asserting Task network outbound remediation for security groups {remediation_error}."

                attempt_retry_probe(
                    error_log=error_log,
                    retry=retry,
                    current_iteration_time=current_iteration_time,
                    max_duration_to_iterate=max_duration_to_iterate,
                    sleep_duration=sleep_duration,
                )
                current_iteration_time += sleep_duration
            else:
                logger.info(
                    "Succeeded asserting network outbound remediated from rollback."
                )
                break
    else:
        error_log = f"{function_name} - Rollback config empty."
        logger.error(error_log)
        raise AssertionError(error_log)


def assert_task_definition_deleted(
    region: str,
    target: str,
    retry: bool = False,
    max_duration_to_iterate: int = 30,
    sleep_duration: int = 15,
):
    function_name = inspect.stack()[0][3]

    client = boto3.client("ecs", region_name=region)

    current_iteration_time = 0
    while True:
        try:
            response = client.describe_task_definition(taskDefinition=target)
            error_log = f"{function_name} - Task definition {target} still exists in region {region}."
            attempt_retry_probe(
                error_log=error_log,
                retry=retry,
                current_iteration_time=current_iteration_time,
                max_duration_to_iterate=max_duration_to_iterate,
                sleep_duration=sleep_duration,
            )
            current_iteration_time += sleep_duration
        except ClientError:
            logger.info(
                f"{function_name} - Assertion Success. Task definition {target} has been deleted in region {region}."
            )
            break


def assert_task_definition_deregistered(
    region: str,
    target: str,
    retry: bool = False,
    max_duration_to_iterate: int = 30,
    sleep_duration: int = 15,
):
    function_name = inspect.stack()[0][3]
    client = boto3.client("ecs", region_name=region)

    current_iteration_time = 0
    while True:
        try:
            response = client.describe_task_definition(taskDefinition=target)
            if response["taskDefinition"]["status"] == "ACTIVE":
                error_log = f"{function_name} - Task definition {target} is still active in region {region}."
                attempt_retry_probe(
                    error_log=error_log,
                    retry=retry,
                    current_iteration_time=current_iteration_time,
                    max_duration_to_iterate=max_duration_to_iterate,
                    sleep_duration=sleep_duration,
                )
                current_iteration_time += sleep_duration
            else:
                logger.info(
                    f"{function_name} - Assertion Success. Task definition {target} has been deregistered in region {region}."
                )
                break
        except ClientError as e:
            error_log = f"Task definition {target} does not exist in region {region}."
            logger.error(error_log)
            raise AssertionError(error_log)


def assert_task_definition_remediated(
    region: str,
    target: str,
    rollback_bucket_name: str,
    rollback_file_name: str,
    retry: bool = False,
    max_duration_to_iterate: int = 30,
    sleep_duration: int = 15,
):
    function_name = inspect.stack()[0][3]
    ecs_client = boto3.client("ecs", region_name=region)
    s3_client = boto3.client("s3", region_name=region)

    rollback_file = s3_client.get_object(
        Bucket=rollback_bucket_name, Key=rollback_file_name
    )
    if rollback_config := json.loads(rollback_file["Body"].read().decode("utf-8")):

        task_definitions = list(rollback_config.keys())

        if target not in task_definitions:
            error_log = f"{function_name} - Task definition {target} not found in rollback config."
            logger.error(error_log)
            raise AssertionError(error_log)

        current_iteration_time = 0
        while True:
            try:
                response = ecs_client.describe_task_definition(taskDefinition=target)
                if response["taskDefinition"]["status"] == "ACTIVE":
                    logger.info(
                        f"{function_name} - Assertion Success. Task definition {target} is ACTIVE in region {region}."
                    )
                    break
                else:
                    error_log = f"{function_name} - Task definition {target} is not ACTIVE in region {region}."
                    attempt_retry_probe(
                        error_log=error_log,
                        retry=retry,
                        current_iteration_time=current_iteration_time,
                        max_duration_to_iterate=max_duration_to_iterate,
                        sleep_duration=sleep_duration,
                    )
                    current_iteration_time += sleep_duration
            except ClientError as e:
                error_log = f"{function_name} - Task definition {target} not found in region {region}."
                attempt_retry_probe(
                    error_log=error_log,
                    retry=retry,
                    current_iteration_time=current_iteration_time,
                    max_duration_to_iterate=max_duration_to_iterate,
                    sleep_duration=sleep_duration,
                )
                current_iteration_time += sleep_duration
    else:
        error_log = f"{function_name} - Rollback config empty."
        logger.error(error_log)
        raise AssertionError(error_log)
