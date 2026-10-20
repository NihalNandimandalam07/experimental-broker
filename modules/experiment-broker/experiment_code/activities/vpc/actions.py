import sys
import logging
from typing import Literal
import boto3
from botocore.exceptions import ClientError
import json
from pprint import pformat


handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

S3_BUCKET_NAME = "experiment-broker-test-rollback-bucket"


from activities.vpc.shared import (
    get_vpc_ids_by_tag,
    parse_test_target_type_vpc,
    parse_test_target_type_az,
    parse_test_target_type_subnet,
    create_blackhole_nacl_in_vpc,
    create_blackhole_route_table_in_vpc,
    associate_subnets_with_blackhole_nacls,
    associate_subnets_with_blackhole_route_tables,
)


def disable_region_by_vpcs_blackhole_nacl(
    # probably temp var (?) need it since using auth token for boto3
    profile_name: str,
    region: str = "us-east-1",
    test_target_type: Literal["RANDOM", "ID_LIST", "ALL"] = "RANDOM",
    targets: list[str] = None,
    state_file_name: str = "disable_us_east_1_by_vpcs_blackhole_nacl.json",
):
    """
    Disables a region by creating a blackhole NACLs in VPCs and attaching them to subnets, the subnets are identified via VPCs.

    Args:
        region (str): Region to disable.
        test_target_type (str): How VPCs are targeted.
        targets (list[str]): List of VPC IDs to disable.
        state_file_name (str): Name of the state file.
    """

    logger.info(
        pformat(
            f"""Running disable_region_by_vpcs_blackhole_nacl with options: 
        Region: {region}
        Test Target Type: {test_target_type}
        Targets: {targets} 
        State File Name: {state_file_name}"""
        )
    )

    session = boto3.Session(profile_name=profile_name)
    ec2_client = session.client("ec2", region_name=region)

    vpc_id_list: list[str] = parse_test_target_type_vpc(
        test_target_type=test_target_type,
        vpc_id_list=targets,
        ec2_client=ec2_client,
    )

    logger.info(pformat(f"Vpc IDs: {str(vpc_id_list)}"))

    rollback_config = {
        "subnet_association_id_old_nacl_id_pairs": {},
    }

    subnets: list[dict] = ec2_client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": vpc_id_list}]
    )["Subnets"]

    logger.info(
        pformat(
            f"Subnet IDs found for Vpc IDS: {str([subnet['SubnetId'] for subnet in subnets])}"
        )
    )

    for vpc_id in vpc_id_list:

        blackhole_nacl_id: str = create_blackhole_nacl_in_vpc(
            vpc_id=vpc_id, ec2_client=ec2_client
        )

        subnet_association_id_old_nacl_id_pairs: dict = (
            associate_subnets_with_blackhole_nacls(
                subnets=[subnet for subnet in subnets if subnet["VpcId"] == vpc_id],
                vpc_id_blackhole_nacl_id_pairs={vpc_id: blackhole_nacl_id},
                ec2_client=ec2_client,
            )
        )

        rollback_config["subnet_association_id_old_nacl_id_pairs"] = {
            **rollback_config["subnet_association_id_old_nacl_id_pairs"],
            **subnet_association_id_old_nacl_id_pairs,
        }

    logger.info(pformat(f"Saving Rollback Config: {str(rollback_config)}"))

    s3_client = session.client("s3", region_name=region)
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=state_file_name,
        Body=json.dumps(rollback_config),
    )

    # save_rollback_config(
    #     rollback_config=rollback_config,
    #     filename=state_file_name,
    #     configuration=None,
    # )


def disable_region_by_azs_blackhole_nacl(
    profile_name: str,
    region: str = "us-east-1",
    test_target_type: Literal["RANDOM", "NAMED_LIST", "ALL"] = "RANDOM",
    targets: list[str] = None,
    state_file_name: str = "disable_regions_by_azs_blackhole_nacl.json",
):
    """
    Disables a region by creating a blackhole NACLs in VPCs and attaching them to subnets, the subnets are identified via AZs.

    Args:
        region (str): Region to disable.
        test_target_type (str): How AZs are targeted.
        targets (list[str]): List of AZ ids to disable.
        state_file_name (str): Name of the state file.
    """

    logger.info(
        pformat(
            f"""Running disable_region_by_azs_blackhole_nacl with options: 
        Region: {region}
        Test Target Type: {test_target_type}
        Targets: {targets} 
        State File Name: {state_file_name}"""
        )
    )

    session = boto3.Session(profile_name=profile_name)
    ec2_client = session.client("ec2", region_name=region)

    az_id_list: list[str] = parse_test_target_type_az(
        test_target_type=test_target_type,
        az_id_list=targets,
        ec2_client=ec2_client,
    )

    logger.info(pformat(f"AZ IDs: {str(az_id_list)}"))

    rollback_config = {
        "subnet_association_id_old_nacl_id_pairs": {},
    }

    subnets: list[dict] = ec2_client.describe_subnets(
        Filters=[{"Name": "availability-zone-id", "Values": az_id_list}]
    )["Subnets"]

    logger.info(
        pformat(
            f"Subnet IDs found for AZ IDS: {str([subnet['SubnetId'] for subnet in subnets])}"
        )
    )

    vpc_id_blackhole_nacl_id_pairs = {}
    vpc_id_list = list(set([subnet["VpcId"] for subnet in subnets]))
    for vpc_id in vpc_id_list:
        blackhole_nacl_id = create_blackhole_nacl_in_vpc(
            vpc_id=vpc_id,
            ec2_client=ec2_client,
        )

        vpc_id_blackhole_nacl_id_pairs[vpc_id] = blackhole_nacl_id

    subnet_association_id_old_nacl_id_pairs: dict = (
        associate_subnets_with_blackhole_nacls(
            subnets=subnets,
            vpc_id_blackhole_nacl_id_pairs=vpc_id_blackhole_nacl_id_pairs,
            ec2_client=ec2_client,
        )
    )

    rollback_config["subnet_association_id_old_nacl_id_pairs"] = {
        **rollback_config["subnet_association_id_old_nacl_id_pairs"],
        **subnet_association_id_old_nacl_id_pairs,
    }

    logger.info(pformat(f"Saving Rollback Config: {str(rollback_config)}"))

    s3_client = session.client("s3", region_name=region)
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=state_file_name,
        Body=json.dumps(rollback_config),
    )

    # save_rollback_config(
    #     rollback_config=rollback_config,
    #     filename=state_file_name,
    #     configuration=None,
    # )


def disable_region_by_subnets_blackhole_nacl(
    profile_name: str,
    region: str = "us-east-1",
    test_target_type: Literal["RANDOM", "NAMED_LIST", "ALL"] = "RANDOM",
    targets: list[str] = None,
    state_file_name: str = "disable_us_east_1_by_subnets_blackhole_nacl.json",
):
    """
    Disables a region by creating a blackhole NACLs in VPCs and attaching them to subnets.

    Args:
        region (str): Region to disable.
        test_target_type (str): How VPCs are targeted.
        targets (list[str]): List of subnet IDs to disable.
        state_file_name (str): Name of the state file.
    """

    logger.info(
        pformat(
            f"""Running disable_region_by_subnets_blackhole_nacl with options: 
        Region: {region}
        Test Target Type: {test_target_type}
        Targets: {targets} 
        State File Name: {state_file_name}"""
        )
    )

    session = boto3.Session(profile_name=profile_name)
    ec2_client = session.client("ec2", region_name=region)

    subnet_id_list: list[str] = parse_test_target_type_subnet(
        test_target_type=test_target_type,
        subnet_id_list=targets,
        ec2_client=ec2_client,
    )

    rollback_config = {
        "subnet_association_id_old_nacl_id_pairs": {},
    }

    subnets: list[dict] = ec2_client.describe_subnets(SubnetIds=subnet_id_list)[
        "Subnets"
    ]

    logger.info(
        pformat(f"Subnet IDs: {str([subnet['SubnetId'] for subnet in subnets])}")
    )

    vpc_id_blackhole_nacl_id_pairs = {}
    vpc_id_list = list(set([subnet["VpcId"] for subnet in subnets]))
    for vpc_id in vpc_id_list:
        blackhole_nacl_id = create_blackhole_nacl_in_vpc(
            vpc_id=vpc_id,
            ec2_client=ec2_client,
        )

        vpc_id_blackhole_nacl_id_pairs[vpc_id] = blackhole_nacl_id

    subnet_association_id_old_nacl_id_pairs: dict = (
        associate_subnets_with_blackhole_nacls(
            subnets=subnets,
            vpc_id_blackhole_nacl_id_pairs=vpc_id_blackhole_nacl_id_pairs,
            ec2_client=ec2_client,
        )
    )

    rollback_config["subnet_association_id_old_nacl_id_pairs"] = {
        **rollback_config["subnet_association_id_old_nacl_id_pairs"],
        **subnet_association_id_old_nacl_id_pairs,
    }

    logger.info(pformat(f"Saving Rollback Config: {str(rollback_config)}"))

    s3_client = session.client("s3", region_name=region)
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=state_file_name,
        Body=json.dumps(rollback_config),
    )
    # save_rollback_config(
    #     rollback_config=rollback_config,
    #     filename=state_file_name,
    #     configuration=None,
    # )


def disable_region_by_vpcs_blackhole_route_table(
    profile_name: str,
    region: str = "us-east-1",
    test_target_type: Literal["RANDOM", "NAMED_LIST", "ALL"] = "RANDOM",
    targets: list[str] = None,
    state_file_name: str = "disable_regions_by_vpcs_blackhole_route_table.json",
):
    session = boto3.Session(profile_name=profile_name)
    ec2_client = session.client("ec2", region_name=region)

    logger.info(
        pformat(
            f"""Running disable_region_by_vpcs_blackhole_route_table with options: 
        Region: {region}
        Test Target Type: {test_target_type}
        Targets: {targets} 
        State File Name: {state_file_name}"""
        )
    )

    vpc_id_list: list[str] = parse_test_target_type_vpc(
        test_target_type=test_target_type,
        vpc_id_list=targets,
        ec2_client=ec2_client,
    )

    logger.info(pformat(f"Vpc IDs: {str(vpc_id_list)}"))

    rollback_config = {
        "subnet_association_id_old_route_table_id_pairs": {},
    }

    subnets: list[dict] = ec2_client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": vpc_id_list}]
    )["Subnets"]

    logger.info(
        pformat(
            f"Subnet IDs found for Vpc IDS: {str([subnet['SubnetId'] for subnet in subnets])}"
        )
    )

    for vpc_id in vpc_id_list:

        blackhole_route_table_id: str = create_blackhole_route_table_in_vpc(
            vpc_id=vpc_id, ec2_client=ec2_client
        )

        subnet_association_id_old_route_table_id_pairs: dict = (
            associate_subnets_with_blackhole_route_tables(
                subnets=[subnet for subnet in subnets if subnet["VpcId"] == vpc_id],
                vpc_id_blackhole_route_table_id_pairs={
                    vpc_id: blackhole_route_table_id
                },
                ec2_client=ec2_client,
            )
        )

        rollback_config["subnet_association_id_old_route_table_id_pairs"] = {
            **rollback_config["subnet_association_id_old_route_table_id_pairs"],
            **subnet_association_id_old_route_table_id_pairs,
        }

    logger.info(pformat(f"Saving Rollback Config: {str(rollback_config)}"))

    s3_client = session.client("s3", region_name=region)
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=state_file_name,
        Body=json.dumps(rollback_config),
    )

    # save_rollback_config(
    #     rollback_config=rollback_config,
    #     filename=state_file_name,
    #     configuration=None,
    # )


def disable_region_by_azs_blackhole_route_table(
    profile_name: str,
    region: str = "us-east-1",
    test_target_type: Literal["RANDOM", "NAMED_LIST", "ALL"] = "RANDOM",
    targets: list[str] = None,
    state_file_name: str = "disable_regions_by_azs_blackhole_route_table.json",
):
    """
    Disables a region by creating a blackhole RouteTables in VPCs and attaching them to subnets, the subnets are identified via AZs.

    Args:
        region (str): Region to disable.
        test_target_type (str): How AZs are targeted.
        targets (list[str]): List of AZ ids to disable.
        state_file_name (str): Name of the state file.
    """
    logger.info(
        pformat(
            f"""Running disable_region_by_vpcs_blackhole_nacl with options: 
        Region: {region}
        Test Target Type: {test_target_type}
        Targets: {targets} 
        State File Name: {state_file_name}"""
        )
    )

    session = boto3.Session(profile_name=profile_name)
    ec2_client = session.client("ec2", region_name=region)

    az_id_list: list[str] = parse_test_target_type_az(
        test_target_type=test_target_type,
        az_id_list=targets,
        ec2_client=ec2_client,
    )

    logger.info(pformat(f"AZ IDs: {str(az_id_list)}"))

    rollback_config = {
        "subnet_association_id_old_route_table_id_pairs": {},
    }

    subnets: list[dict] = ec2_client.describe_subnets(
        Filters=[{"Name": "availability-zone-id", "Values": az_id_list}]
    )["Subnets"]

    logger.info(
        pformat(
            f"Subnet IDs found for AZ IDS: {str([subnet['SubnetId'] for subnet in subnets])}"
        )
    )

    vpc_id_blackhole_route_table_id_pairs = {}
    vpc_id_list = list(set([subnet["VpcId"] for subnet in subnets]))
    for vpc_id in vpc_id_list:
        blackhole_route_table_id = create_blackhole_route_table_in_vpc(
            vpc_id=vpc_id,
            ec2_client=ec2_client,
        )

        vpc_id_blackhole_route_table_id_pairs[vpc_id] = blackhole_route_table_id

    subnet_association_id_old_route_table_id_pairs: dict = (
        associate_subnets_with_blackhole_route_tables(
            subnets=subnets,
            vpc_id_blackhole_route_table_id_pairs=vpc_id_blackhole_route_table_id_pairs,
            ec2_client=ec2_client,
        )
    )

    rollback_config["subnet_association_id_old_route_table_id_pairs"] = {
        **rollback_config["subnet_association_id_old_route_table_id_pairs"],
        **subnet_association_id_old_route_table_id_pairs,
    }

    logger.info(pformat(f"Saving Rollback Config: {str(rollback_config)}"))

    s3_client = session.client("s3", region_name=region)
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=state_file_name,
        Body=json.dumps(rollback_config),
    )

    # save_rollback_config(
    #     rollback_config=rollback_config,
    #     filename=state_file_name,
    #     configuration=None,
    # )


def disable_region_by_subnets_blackhole_route_table(
    profile_name: str,
    region: str = "us-east-1",
    test_target_type: Literal["RANDOM", "NAMED_LIST", "ALL"] = "RANDOM",
    targets: list[str] = None,
    state_file_name: str = "disable_us_east_1_by_subnets_blackhole_route_table.json",
):
    logger.info(
        pformat(
            f"""Running disable_region_by_vpcs_blackhole_nacl with options: 
        Region: {region}
        Test Target Type: {test_target_type}
        Targets: {targets} 
        State File Name: {state_file_name}"""
        )
    )

    session = boto3.Session(profile_name=profile_name)
    ec2_client = session.client("ec2", region_name=region)

    subnet_id_list: list[str] = parse_test_target_type_subnet(
        test_target_type=test_target_type,
        subnet_id_list=targets,
        ec2_client=ec2_client,
    )

    rollback_config = {
        "subnet_association_id_old_route_table_id_pairs": {},
    }

    subnets: list[dict] = ec2_client.describe_subnets(SubnetIds=subnet_id_list)[
        "Subnets"
    ]

    logger.info(
        pformat(f"Subnet IDs: {str([subnet['SubnetId'] for subnet in subnets])}")
    )

    vpc_id_blackhole_route_table_id_pairs = {}
    vpc_id_list = list(set([subnet["VpcId"] for subnet in subnets]))
    for vpc_id in vpc_id_list:
        blackhole_route_table_id = create_blackhole_route_table_in_vpc(
            vpc_id=vpc_id,
            ec2_client=ec2_client,
        )

        vpc_id_blackhole_route_table_id_pairs[vpc_id] = blackhole_route_table_id

    subnet_association_id_old_route_table_id_pairs: dict = (
        associate_subnets_with_blackhole_route_tables(
            subnets=subnets,
            vpc_id_blackhole_route_table_id_pairs=vpc_id_blackhole_route_table_id_pairs,
            ec2_client=ec2_client,
        )
    )

    rollback_config["subnet_association_id_old_route_table_id_pairs"] = {
        **rollback_config["subnet_association_id_old_route_table_id_pairs"],
        **subnet_association_id_old_route_table_id_pairs,
    }

    logger.info(pformat(f"Saving Rollback Config: {str(rollback_config)}"))

    s3_client = session.client("s3", region_name=region)
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=state_file_name,
        Body=json.dumps(rollback_config),
    )
    # save_rollback_config(
    #     rollback_config=rollback_config,
    #     filename=state_file_name,
    #     configuration=None,
    # )


def reenable_region_blackhole_nacl(
    profile_name: str,
    region: str = "us-east-1",
    state_file_name: str = "disable_us_east_1_by_vpcs_nacl.json",
):
    """ """
    session = boto3.Session(profile_name=profile_name)
    s3_client = session.client("s3", region_name=region)
    response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=state_file_name)

    if rollback_config := json.loads(response["Body"].read().decode("utf-8")):
        ec2_client = session.client("ec2", region_name=region)

        logger.info(pformat(f"Loading Rollback Config: {str(rollback_config)}"))
        for blackhole_nacl_association_id, old_nacl_id in rollback_config[
            "subnet_association_id_old_nacl_id_pairs"
        ].items():
            ec2_client.replace_network_acl_association(
                AssociationId=blackhole_nacl_association_id, NetworkAclId=old_nacl_id
            )
            logger.info(
                pformat(
                    f"Replaced NACL Association: {blackhole_nacl_association_id} with original NACL: {old_nacl_id}"
                )
            )

        blackhole_nacl_ids = [
            nacl["NetworkAclId"]
            for nacl in ec2_client.describe_network_acls(
                Filters=[{"Name": "tag:Name", "Values": ["Blackhole"]}]
            )["NetworkAcls"]
        ]

        logger.info(
            pformat(f"Retrieved list of Blackhole NACLs: {str(blackhole_nacl_ids)}")
        )
        for blackhole_nacl_id in blackhole_nacl_ids:
            ec2_client.delete_network_acl(NetworkAclId=blackhole_nacl_id)
            logger.info(pformat(f"Deleted Blackhole NACL: {blackhole_nacl_id}"))


def reenable_region_blackhole_route_table(
    profile_name: str,
    region: str = "us-east-1",
    state_file_name: str = "disable_us_east_1_by_vpcs_route_table.json",
):
    """ """
    session = boto3.Session(profile_name=profile_name)
    s3_client = session.client("s3", region_name=region)
    response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=state_file_name)

    if rollback_config := json.loads(response["Body"].read().decode("utf-8")):
        ec2_client = session.client("ec2", region_name=region)

        logger.info(pformat(f"Loading Rollback Config: {str(rollback_config)}"))
        for blackhole_route_table_association_id, old_route_table_id in rollback_config[
            "subnet_association_id_old_route_table_id_pairs"
        ].items():
            ec2_client.replace_route_table_association(
                AssociationId=blackhole_route_table_association_id,
                RouteTableId=old_route_table_id,
            )
            logger.info(
                pformat(
                    f"Replaced Route Table Association: {blackhole_route_table_association_id} with original Route Table: {old_route_table_id}"
                )
            )

        blackhole_route_table_ids = [
            route_table["RouteTableId"]
            for route_table in ec2_client.describe_route_tables(
                Filters=[{"Name": "tag:Name", "Values": ["Blackhole"]}]
            )["RouteTables"]
        ]

        logger.info(
            pformat(
                f"Retrieved list of Blackhole Route Tables: {str(blackhole_route_table_ids)}"
            )
        )
        for blackhole_route_table_id in blackhole_route_table_ids:
            ec2_client.delete_route_table(RouteTableId=blackhole_route_table_id)
            logger.info(
                pformat(f"Deleted Blackhole Route Table: {blackhole_route_table_id}")
            )
