from typing import Dict, List
from chaosaws import aws_client
from chaoslib.types import Configuration
from logzero import logger


def apply_new_nacl(
    nacl_associations: Dict[str, str],
    new_nacl_id: str,
    configuration: Configuration = None,
):
    """Apply a new NACL association."""
    ec2 = aws_client("ec2", configuration=configuration)
    rollback_config = {}

    logger.info("Updating NACL Asssociations...")
    for nacl_association_id, current_nacl_id in nacl_associations.items():
        response = ec2.replace_network_acl_association(
            AssociationId=nacl_association_id, NetworkAclId=new_nacl_id
        )
        rollback_config[response["NewAssociationId"]] = current_nacl_id

    logger.info("NACL Associations updated.")
    return rollback_config


def get_subnets_in_az(
    vpc_id: str, availability_zone: str, configuration: Configuration = None
):
    """Return a list of SubnetId(s) for specified AZ."""
    ec2 = aws_client("ec2", configuration=configuration)
    subnets_response = ec2.describe_subnets(
        Filters=[
            {
                "Name": "availability-zone",
                "Values": [availability_zone],
            },
            {
                "Name": "vpc-id",
                "Values": [vpc_id],
            },
        ]
    )
    subnets = {subnet["SubnetId"] for subnet in subnets_response["Subnets"]}
    logger.info(
        "Subnets in VPC [%s] - AZ [%s]: %s",
        vpc_id,
        availability_zone,
        subnets.join(","),
    )
    return subnets


def get_subnets_nacl_associations(
    subnets: List[str], configuration: Configuration = None
):
    """Return a list of NACL Associations for the given SubnetIds."""
    ec2 = aws_client("ec2", configuration=configuration)
    nacls = ec2.describe_network_acls(
        Filters=[
            {
                "Name": "association.subnet-id",
                "Values": subnets,
            },
        ]
    )["NetworkAcls"]

    nacl_associations = {}

    for nacl in nacls:
        for nacl_association in nacl["Associations"]:
            if nacl_association["SubnetId"] in subnets:
                nacl_associations[nacl_association["NetworkAclAssociationId"]] = (
                    nacl_association["NetworkAclId"]
                )

    return nacl_associations
