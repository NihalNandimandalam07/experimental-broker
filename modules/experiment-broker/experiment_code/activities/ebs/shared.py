import logging
from typing import List

import boto3
from botocore.exceptions import ClientError


logging.basicConfig(level=logging.ERROR)


def get_ebs_volume_by_tag(tag_key_1, tag_value_1, tag_key_2, tag_value_2, return_value):
    session = boto3.Session()
    ec2 = session.client("ec2", "us-east-1")

    res = ec2.describe_volumes(
        Filters=[
            {
                "Name": f"{tag_key_1}",
                "Values": [
                    f"{tag_value_1}",
                ],
            },
            {
                "Name": f"{tag_key_2}",
                "Values": [
                    f"{tag_value_2}",
                ],
            },
        ]
    )

    return res["Volumes"][0]["Attachments"][0][f"{return_value}"]
