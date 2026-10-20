import sys
import logging
import boto3
import logging
from typing import List
from botocore.exceptions import ClientError
from typing import List
from activities.ec2.shared import get_test_instance_ids
from activities.network.shared import get_ip_ranges

logging.basicConfig(level=logging.ERROR)


def blackhole_s3(
    targets: List[str] = None,
    test_target_type: str = None,
    tag_key: str = None,
    tag_value: str = None,
    region: str = None,
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

    s3_ip_ranges = get_ip_ranges(region=region, managed_service="S3")

    parameters = {
        "duration": [
            duration,
        ],
        "ipAddresses": [
            s3_ip_ranges,
        ],
    }

    session = boto3.Session()
    ssm = session.client("ssm", region)
    try:
        response = ssm.send_command(
            DocumentName="BlackHoleByIPAddress",
            InstanceIds=test_instance_ids,
            CloudWatchOutputConfig={"CloudWatchOutputEnabled": True},
            Parameters=parameters,
        )
    except ClientError as e:
        logging.error(e)
        raise

    return response
