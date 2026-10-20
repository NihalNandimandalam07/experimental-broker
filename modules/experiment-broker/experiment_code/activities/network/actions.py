#!/bin/python3

import logging
import sys
import boto3
from typing import List
from botocore.exceptions import ClientError
from activities.ec2.shared import get_test_instance_ids

logging.basicConfig(level=logging.ERROR)

"""
This function should be removed and the experiment should call black_hole_by_port.
"""


def point_inactive_dns(
    targets: List[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = None,
):
    """Runs SSM command BlackholeDNS.yml on all targets with specified tag key and value to block DNS"""

    function_name = sys._getframe().f_code.co_name

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logging.info(function_name, "(): test_instance_ids= ", test_instance_ids)

    session = boto3.Session()
    ssm = session.client("ssm", region)

    try:
        response = ssm.send_command(
            InstanceIds=test_instance_ids,
            CloudWatchOutputConfig={"CloudWatchOutputEnabled": True},
            DocumentName="BlackholeDNS",
        )
    except ClientError as e:
        logging.error(e)
        raise

    return response


def blackhole_by_url(
    targets: List[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    urls: str = None,
):
    """Runs SSM command BlackHoleByURL.yml on all targets with specified tag key and value"""

    function_name = sys._getframe().f_code.co_name

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )

    parameters = {
        "urls": [
            urls,
        ],
    }

    logging.info(function_name, "(): test_instance_ids= ", test_instance_ids)

    session = boto3.Session()
    ssm = session.client("ssm", region)

    try:
        ssm.send_command(
            InstanceIds=test_instance_ids,
            CloudWatchOutputConfig={"CloudWatchOutputEnabled": True},
            DocumentName="BlackHoleByURL",
            Parameters=parameters,
        )
    except ClientError as e:
        logging.error(e)


def blackhole_secrets_manager(
    targets: List[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    duration: str = None,
):
    function_name = sys._getframe().f_code.co_name

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    print(function_name, "(): test_instance_ids= ", test_instance_ids)

    secrets_manager_ip_ranges = get_ip_ranges(
        region="us-east-1", managed_service="secretsmanager"
    )

    parameters = {
        "duration": [
            duration,
        ],
        "ipAddresses": [
            secrets_manager_ip_ranges,
        ],
    }

    session = boto3.Session()
    ssm = session.client("ssm", region)
    try:
        response = ssm.send_command(
            DocumentName="BlackholeByIPAddress",
            InstanceIds=test_instance_ids,
            CloudWatchOutputConfig={"CloudWatchOutputEnabled": True},
            Parameters=parameters,
        )
    except ClientError as e:
        logging.error(e)
        raise

    return response
