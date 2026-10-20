import sys
import logging
from typing import List
import boto3
from botocore.exceptions import ClientError
from activities.ec2.shared import get_test_instance_ids
from activities.network.shared import get_ip_ranges

logging.basicConfig(level=logging.ERROR)
logging.Formatter(fmt="%(funcName)s: %(message)s")


def blackhole_dynamodb(
    targets: List[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    duration: str = None,
):
    """Blackholes DynamoDB.

    Args:
        targets (List[str], optional): _description_. Defaults to None.
        test_target_type (str, optional): _description_. Defaults to "RANDOM".
        tag_key (str, optional): _description_. Defaults to None.
        tag_value (str, optional): _description_. Defaults to None.
        region (str, optional): _description_. Defaults to "us-east-1".
        duration (str, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logging.debug(f"test_instance_ids={test_instance_ids}")

    dynamodb_ip_ranges = get_ip_ranges(region="us-east-1", managed_service="DYNAMODB")

    parameters = {
        "duration": [
            duration,
        ],
        "ipAddresses": [
            dynamodb_ip_ranges,
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
