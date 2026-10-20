import sys
import boto3
import time
import inspect

from logzero import logger
from re import I

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
