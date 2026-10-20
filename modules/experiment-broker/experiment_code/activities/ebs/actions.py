import boto3
import logging
from typing import List
from botocore.exceptions import ClientError
from activities.ec2.shared import get_test_instance_ids
from activities.ebs.shared import get_ebs_volume_by_tag


def detach_volume(
    region: str = None,
    name_space: str = None,
    pod_name_pattern: str = None,
    tag_key_1: str = None,
    tag_value_1: str = None,
    tag_key_2: str = None,
    tag_value_2: str = None,
):
    # The instance on which we run the SSM Document that deletes the pod
    # is hardcoded below - it should probably be a Python setup variable.
    command_execution_intance = get_test_instance_ids(
        test_target_type="RANDOM",
        tag_key="tag:Name",
        tag_value="nodes.activities-us-east-1.k8s.local",
    )

    parameters = {
        "volumeId": [
            get_ebs_volume_by_tag(
                tag_key_1, tag_value_1, tag_key_2, tag_value_2, "VolumeId"
            )
        ],
        "device": [
            get_ebs_volume_by_tag(
                tag_key_1, tag_value_1, tag_key_2, tag_value_2, "Device"
            )
        ],
    }

    print(f"Volume to be detached: {parameters['volumeId'][0]}")
    print(f"Device to be detached: {parameters['device'][0]}")
    session = boto3.Session()
    ssm = session.client("ssm", region)

    try:
        response = ssm.send_command(
            DocumentName="DetachVolume",
            InstanceIds=command_execution_intance,
            CloudWatchOutputConfig={"CloudWatchOutputEnabled": True},
            Parameters=parameters,
            OutputS3BucketName="resiliency-ssm-command-output",
        )

    except ClientError as e:
        logging.error(e)
        raise

    return True
