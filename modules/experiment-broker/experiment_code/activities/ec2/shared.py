import sys
import boto3
import logging
import inspect

from botocore.exceptions import ClientError
from random import randint, choice
from typing import Any, Dict, List

logging.basicConfig(level=logging.ERROR)


def get_random_instance_id_by_tag(tagKey, tagValue, region="us-east-1"):
    """Returns an instance id from a given tagname"""

    function_name = inspect.stack()[0][3]

    session = boto3.Session()
    ec2 = session.client("ec2", region)

    filters = [
        {
            "Name": tagKey,
            "Values": [tagValue],
        },
    ]
    print(function_name, "(): filters = ", filters)

    instance_list = ec2.describe_instances(Filters=filters)
    instance_id = None

    num_instances = len(instance_list["Reservations"])
    print(function_name, "(): num_instances = ", num_instances)

    if num_instances <= 0:
        logging.error("Error with finding instance-id")
        return 0

    index = randint(0, num_instances - 1)
    instance_id = instance_list["Reservations"][index]["Instances"][0]["InstanceId"]
    print(function_name, "(): instance_id: = ", instance_id)

    return instance_id


def get_all_instance_ids_by_tag(tagKey, tagValue, region="us-east-1"):
    """Returns a list of instance ida from a given tagname"""

    function_name = inspect.stack()[0][3]

    session = boto3.Session()
    ec2 = session.client("ec2", region)

    instance_list = ec2.describe_instances(
        Filters=[
            {
                "Name": tagKey,
                "Values": [tagValue],
            },
        ],
    )
    instance_ids = []

    num_instances = len(instance_list["Reservations"])
    print(function_name, "(): num_instances = ", num_instances)

    if num_instances <= 0:
        logging.error("Error with finding instance-id")
        return instance_ids

    for instance in instance_list["Reservations"]:
        instance_ids.append(instance["Instances"][0]["InstanceId"])

    return instance_ids


def get_test_instance_ids(
    test_target_type: str = "RANDOM",
    tag_key: str = "tag:Name",
    tag_value: str = "nodes.activities-us-east-1.k8s.local",
    instance_ids: List[str] = None,
    region="us-east-1",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = []

    if test_target_type == "RANDOM":
        test_instance_id = get_random_instance_id_by_tag(
            tag_key, tag_value, region=region
        )
        print(function_name, "(): test_instance_id = ", test_instance_id)
        test_instance_ids = [
            test_instance_id,
        ]
    elif test_target_type == "ALL":
        test_instance_ids = get_all_instance_ids_by_tag(
            tag_key, tag_value, region=region
        )
        print(test_instance_ids)
    elif test_target_type == "NAMED_LIST":
        test_instance_ids = instance_ids
    else:
        logging.error("Illegal test target type specified.")
        return False

    logging.info(
        function_name, ": get_test_targets(): test_targets = ", test_instance_ids
    )

    return test_instance_ids


def get_instance_profile_name(tagKey, tagValue, region="us-east-1"):
    """Returns a str of instance IAM profile instances 'name' from a given tagname"""

    function_name = inspect.stack()[0][3]

    session = boto3.Session()
    ec2 = session.client("ec2", region)

    instance_list = ec2.describe_instances(
        Filters=[
            {
                "Name": tagKey,
                "Values": [tagValue],
            },
        ],
    )

    instance_profile_arn = instance_list["Reservations"][0]["Instances"][0][
        "IamInstanceProfile"
    ]["Arn"]

    return instance_profile_arn.split("/")[1]


def get_role_from_instance_profile(instanceProfile: str = None):
    session = boto3.Session()
    iam = session.client("iam", "us-east-1")

    instance_profile = iam.get_instance_profile(InstanceProfileName=instanceProfile)
    # print(instance_profile['InstanceProfile']['Roles'][0]['RoleName'])
    return instance_profile["InstanceProfile"]["Roles"][0]["RoleName"]


def remove_ec2_security_groups(
    instance_id: str,
    region: str = "us-east-1",
    severity: str = "RANDOM",
    temp_sg_tag_key: str = "source",
    temp_sg_tag_value: str = "resiliency_temp",
    temp_sg_name: str = "resiliency_temp",
):
    resource = boto3.resource("ec2", region)
    client = boto3.client("ec2", region)

    instance = resource.instance(instance_id)
    final_sg = []

    try:
        if severity == "RANDOM":
            for sg in instance.security_groups:
                if choice[True, False]:
                    final_sg.append(sg)

        elif severity == "MAX":
            response = client.describe_security_groups(
                Filters=[
                    {"Name": "tag:" + temp_sg_tag_key, "Values": [temp_sg_tag_value]}
                ]
            )
            if not response["SecurityGroups"]:
                sg_creation = client.create_security_group(
                    Description="Temp Security Group for Resiliency Testing",
                    GroupName=temp_sg_name,
                    VpcId=instance.vpc_id,
                    TagSpecifications=[
                        {
                            "ResourceType": "security-group",
                            "Tags": [
                                {"Key": temp_sg_tag_key, "Value": temp_sg_tag_value}
                            ],
                        }
                    ],
                )
                sg_id = sg_creation["GroupId"]
                final_sg.append(sg_id)
        else:
            for sg in instance.security_groups:
                if sg != severity:
                    final_sg.append(sg)
        output = instance.modify_attribute(Groups=final_sg)
        return output
    except ClientError as e:
        logging.error(e)
        raise
