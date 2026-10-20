from chaosaws import aws_client
from boto3 import Session, client
from botocore.exceptions import ClientError

import logging
import random
import boto3

handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)
logger.addHandler(handler)


ALLOWED_TEST_TARGET_TYPES = ["RANDOM", "ID_LIST", "ALL"]


def parse_test_target_type_vpc(
    test_target_type: str,
    vpc_id_list: list[str],
    ec2_client: any,
):

    if test_target_type not in ALLOWED_TEST_TARGET_TYPES:
        raise ValueError(
            f"test_target_type must be one of 'RANDOM', 'ID_LIST', or 'ALL'. Current Value: {test_target_type}"
        )

    vpc_ids = [vpc["VpcId"] for vpc in ec2_client.describe_vpcs()["Vpcs"]]

    if test_target_type == "RANDOM":
        vpc_id_list = random.sample(vpc_ids, random.randint(1, len(vpc_ids)))
    if test_target_type == "ID_LIST":
        set_diff = set(vpc_id_list) - set(vpc_ids)
        if set_diff:
            raise ValueError(f"VPCs do not exist in region: {str(set_diff)}")
    if test_target_type == "ALL":
        vpc_id_list = vpc_ids

    return vpc_id_list


def parse_test_target_type_az(
    test_target_type: str, az_id_list: list[str], ec2_client: any
):

    if test_target_type not in ALLOWED_TEST_TARGET_TYPES:
        raise ValueError(
            f"test_target_type must be one of 'RANDOM', 'ID_LIST', or 'ALL'. Current Value: {test_target_type}"
        )

    az_ids = [
        az["ZoneId"]
        for az in ec2_client.describe_availability_zones()["AvailabilityZones"]
    ]

    if test_target_type == "RANDOM":
        az_id_list = random.sample(az_ids, random.randint(1, len(az_ids)))
    if test_target_type == "ID_LIST":
        set_diff = set(az_id_list) - set(az_ids)
        if set_diff:
            raise ValueError(f"AZs do not exist in region: {str(set_diff)}")
    if test_target_type == "ALL":
        az_id_list = az_ids

    return az_id_list


def parse_test_target_type_subnet(
    test_target_type: str,
    subnet_id_list: list[str],
    ec2_client: any,
):
    if test_target_type not in ALLOWED_TEST_TARGET_TYPES:
        raise ValueError(
            f"test_target_type must be one of 'RANDOM', 'ID_LIST', or 'ALL'. Current Value: {test_target_type}"
        )

    subnet_ids = [
        subnet["SubnetId"] for subnet in ec2_client.describe_subnets()["Subnets"]
    ]

    if test_target_type == "RANDOM":
        subnet_id_list = random.sample(subnet_ids, random.randint(1, len(subnet_ids)))
    if test_target_type == "ID_LIST":
        set_diff = set(subnet_id_list) - set(subnet_ids)
        if set_diff:
            raise ValueError(f"Subnets do not exist in region: {set_diff}")
    if test_target_type == "ALL":
        subnet_id_list = subnet_ids

    return subnet_id_list


def get_vpc_ids_by_tag(
    region: str,
    tag_key: str,
    tag_value: str,
) -> list[str]:
    ec2 = aws_client("ec2", configuration=configuration)
    subnets = ec2.describe_subnets(SubnetIds=subnet_ids)["Subnets"]

    return subnets


def get_subnets_by_az(az_id: str, configuration: Configuration = None) -> list[str]:
    ec2 = aws_client("ec2", configuration=configuration)
    subnets = ec2.describe_subnets(
        Filters=[{"Name": "availability-zone", "Values": [az_id]}]
    )["Subnets"]
    subnet_ids = [subnet["SubnetId"] for subnet in subnets]

    logging.info("Subnet IDs: %s", subnet_ids)
    logging.info("Number of Subnet IDs %s", len(subnet_ids))

    return subnet_ids


def __get_nacl_association_ids_by_subnets(
    subnet_ids: list[str], configuration: Configuration = None
) -> list[dict]:
    ec2 = aws_client("ec2", configuration=configuration)
    nacls = ec2.describe_network_acls(
        Filters=[
            {
                "Name": "association.subnet-id",
                "Values": subnet_ids,
            },
        ]
    )["NetworkAcls"]

    nacl_associations = {}
    for nacl in nacls:
        for nacl_association in nacl["Associations"]:
            if nacl_association["SubnetId"] in subnet_ids:
                nacl_associations[nacl_association["SubnetId"]] = {
                    "NetworkAclAssociationId": nacl_association[
                        "NetworkAclAssociationId"
                    ],
                    "NetworkAclId": nacl_association["NetworkAclId"],
                }

    return nacl_associations


def get_route_table_association_ids_by_subnets(
    subnet_ids: list[str], ec2_client: any
) -> list[dict[str, dict[str, str]]]:
    route_tables = ec2_client.describe_route_tables(
        Filters=[
            {
                "Name": "association.subnet-id",
                "Values": subnet_ids,
            },
        ]
    )["RouteTables"]

    route_table_associations = {}
    for route_table in route_tables:
        for route_table_association in route_table["Associations"]:
            if route_table_association["SubnetId"] in subnet_ids:
                route_table_associations[route_table_association["SubnetId"]] = {
                    "RouteTableAssociationId": route_table_association[
                        "RouteTableAssociationId"
                    ],
                    "RouteTableId": route_table_association["RouteTableId"],
                }

    return route_table_associations


def associate_subnets_with_blackhole_nacls(
    subnets: list[dict], vpc_id_blackhole_nacl_id_pairs: dict[str, str], ec2_client: any
) -> dict[str, str]:

    nacl_associations = get_nacl_association_ids_by_subnets(
        subnet_ids=[subnet["SubnetId"] for subnet in subnets],
        configuration=configuration,
    )

    for subnet in subnets:
        nacl_associations[subnet["SubnetId"]]["VpcId"] = subnet["VpcId"]

    rollback_subnet_association = {}
    for nacl_associations_dict in nacl_associations.values():
        new_nacl_association_id = ec2_client.replace_network_acl_association(
            AssociationId=nacl_associations_dict["NetworkAclAssociationId"],
            NetworkAclId=vpc_id_blackhole_nacl_id_pairs[
                nacl_associations_dict["VpcId"]
            ],
        )["NewAssociationId"]
        rollback_subnet_association[new_nacl_association_id] = nacl_associations_dict[
            "NetworkAclId"
        ]

    return rollback_subnet_association


def associate_subnets_with_blackhole_route_tables(
    subnets: list[dict],
    vpc_id_blackhole_route_table_id_pairs: dict[str, str],
    ec2_client: any,
):
    route_table_associations = get_route_table_association_ids_by_subnets(
        subnet_ids=[subnet["SubnetId"] for subnet in subnets],
        ec2_client=ec2_client,
    )

    for subnet in subnets:
        route_table_associations[subnet["SubnetId"]]["VpcId"] = subnet["VpcId"]

    rollback_subnet_association = {}
    for route_table_associations_dict in route_table_associations.values():
        new_route_table_association_id = ec2_client.replace_route_table_association(
            AssociationId=route_table_associations_dict["RouteTableAssociationId"],
            RouteTableId=vpc_id_blackhole_route_table_id_pairs[
                route_table_associations_dict["VpcId"]
            ],
        )["NewAssociationId"]
        rollback_subnet_association[new_route_table_association_id] = (
            route_table_associations_dict["RouteTableId"]
        )

    return rollback_subnet_association


def create_blackhole_nacl_in_vpc(vpc_id: str, ec2_client: any) -> str:
    """
    Creates a blackhole NACL in the specified VPC.

    Args:
        vpc_id (str): VPC ID.
        ec2_client (any): EC2 client.

    Returns:
        str: NACL ID.
    """

    nacl_id = ec2_client.create_network_acl(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                "ResourceType": "network-acl",
                "Tags": [{"Key": "Name", "Value": "Blackhole"}],
            }
        ],
    )["NetworkAcl"]["NetworkAclId"]

    # Egress
    ec2_client.create_network_acl_entry(
        CidrBlock="0.0.0.0/0",
        Egress=True,
        PortRange={"From": 0, "To": 65535},
        NetworkAclId=nacl_id,
        Protocol="-1",
        RuleAction="deny",
        RuleNumber=100,
    )

    # Ingress
    ec2_client.create_network_acl_entry(
        CidrBlock="0.0.0.0/0",
        Egress=False,
        PortRange={"From": 0, "To": 65535},
        NetworkAclId=nacl_id,
        Protocol="-1",
        RuleAction="deny",
        RuleNumber=100,
    )

    logger.info(f"Blackhole NACL: {str(nacl_id)} created in VPC: {str(vpc_id)}")
    return nacl_id


def create_blackhole_route_table_in_vpc(vpc_id: str, ec2_client: any) -> str:

    route_table_id = ec2_client.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                "ResourceType": "route-table",
                "Tags": [
                    {"Key": "Name", "Value": "Blackhole"},
                ],
            }
        ],
    )["RouteTable"]["RouteTableId"]

    logger.info(
        f"Blackhole Route Table: {str(route_table_id)} created in VPC: {str(vpc_id)}"
    )

    return response["NewAssociationId"]


def restore_nacl_associations():
    pass


def create_blackhole_route_table():
    pass


def assert_subnet_nacl_association_by_tag(
    subnet_id, region, nacl_tag_key, nacl_tag_value
):
    ec2client = client("ec2", region)
    response = ec2client.describe_network_acls(
        Filters=[{"Name": "association.subnet-id", "Values": [subnet_id]}]
    )

    nacls = response["NetworkAcls"]
    if nacls > 0:
        for nacl in nacls:
            nacl_tags = nacl["Tags"]
            if nacl_tags > 0:
                for nacl_tag in nacl_tags:
                    if (
                        nacl_tag["Key"] == nacl_tag_key
                        and nacl_tag["Value"] == nacl_tag_value
                    ):
                        print(
                            f"NACL tags match desired NACL. Key : {nacl_tag_key} with Value : {nacl_tag_value}"
                        )
                        return True
                # this raises an exception if there are no tags on the NACL that match the desired failed NACL
                raise AssertionError("NO NACL MATCH")
            else:
                raise AssertionError("NO TAGS")
    else:
        raise AssertionError("NO NACLS")

    return False


def assert_subnet_nacl_association_by_nacl(subnet_id, region, nacl_id):
    ec2client = client("ec2", region)
    response = ec2client.describe_network_acls(
        Filters=[{"Name": "association.subnet-id", "Values": [subnet_id]}]
    )

    nacls = response["NetworkAcls"]
    if nacls > 0:
        for nacl in nacls:
            nacl_id = nacl["NetworkAclId"]
            if not nacl_id:
                print(f"NACL ID match desired NACL. NACL ID : {nacl_id}")
                return True
                # this raises an exception if there are no tags on the NACL that match the desired failed NACL
            raise AssertionError("NO NACL MATCH")
    else:
        raise AssertionError("NO NACLS")

    return False
