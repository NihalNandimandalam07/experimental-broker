import boto3
import inspect

from logzero import logger

from activities.ec2.shared import get_test_instance_ids
from botocore.exceptions import ClientError


def assert_instance_rebuilt(
    tag_value: str, region: str = "us-east-1", tag_key: str = "tag:Name"
):
    function_name = inspect.stack()[0][3]
    session = boto3.Session()
    ec2client = session.client("ec2", region)
    instance_list = ec2client.describe_instances(
        Filters=[
            {
                "Name": tag_key,
                "Values": [tag_value],
            },
        ]
    )

    instances = instance_list["Reservations"]
    terminated_count = 0
    pending_count = 0
    for instance in instances:
        terminated = len(
            [x for x in instance["Instances"] if x["State"]["Name"] == "terminated"]
        )
        pending = len(
            [x for x in instance["Instances"] if x["State"]["Name"] == "pending"]
        )
        if terminated:
            terminated_count += terminated
        if pending:
            pending_count += pending
    if terminated_count == pending_count:
        return True
    else:
        return False


def check_ec2_instance_running(
    instance_id: str,
    region: str = "us-east-2"
) -> bool:
    """
    Check whether an EC2 instance is running.
    """

    try:
        ec2_client = boto3.client(
            "ec2",
            region_name=region
        )

        response = ec2_client.describe_instances(
            InstanceIds=[instance_id]
        )

        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                state = instance["State"]["Name"]

                logger.info(
                    f"EC2 instance {instance_id} state: {state}"
                )

                return state == "running"

        logger.error(
            f"EC2 instance {instance_id} not found"
        )
        return False

    except ClientError as e:
        logger.error(
            f"Failed to check EC2 instance {instance_id}: {e}"
        )
        return False
