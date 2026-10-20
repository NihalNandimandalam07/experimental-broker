import unittest
from unittest.mock import Mock, patch, call
import re
import json

import activities.vpc.actions

from activities.vpc.actions import (
    disable_region_by_vpcs_blackhole_nacl,
    disable_region_by_azs_blackhole_nacl,
    disable_region_by_subnets_blackhole_nacl,
    disable_region_by_vpcs_blackhole_route_table,
    disable_region_by_azs_blackhole_route_table,
    disable_region_by_subnets_blackhole_route_table,
    reenable_region_blackhole_nacl,
    reenable_region_blackhole_route_table,
)


def get_number(s: str) -> int:
    n = re.findall(r"\d+", s)
    return int(n[0])


class TestDisableRegions(unittest.TestCase):
    ##################
    ### TEST SETUP ###
    ##################
    # Removes the cap on the length of the diff output
    maxDiff = None

    def setUp(self):
        self.mock_boto3_session = patch(
            "activities.vpc.actions.boto3.Session"
        ).start()
        self.mock_boto3_client = self.mock_boto3_session.return_value.client
        self.mock_create_blackhole_nacl_in_vpc = patch(
            "activities.vpc.actions.create_blackhole_nacl_in_vpc"
        ).start()
        self.mock_create_blackhole_nacl_in_vpc.side_effect = (
            self.side_effect_create_blackhole_nacl_in_vpc
        )
        self.mock_create_blackhol_route_table_in_vpc = patch(
            "activities.vpc.actions.create_blackhole_route_table_in_vpc"
        ).start()
        self.mock_create_blackhol_route_table_in_vpc.side_effect = (
            self.side_effect_create_blackhole_route_table_in_vpc
        )
        self.mock_associate_subnets_with_blackhole_nacls = patch(
            "activities.vpc.actions.associate_subnets_with_blackhole_nacls"
        ).start()

        self.mock_associate_subnets_with_blackhole_route_tables = patch(
            "activities.vpc.actions.associate_subnets_with_blackhole_route_tables"
        ).start()

        self.mock_logger = patch.object(activities.vpc.actions, "logger").start()

    def tearDown(self):
        patch.stopall()

    ####################
    ### SIDE EFFECTS ###
    ####################

    def side_effect_create_blackhole_nacl_in_vpc(self, vpc_id: str, ec2_client: any):
        return f"test-blackhole-nacl-id-{get_number(vpc_id)}"

    def side_effect_create_blackhole_route_table_in_vpc(
        self, vpc_id: str, ec2_client: any
    ):
        return f"test-blackhole-route-table-id-{get_number(vpc_id)}"

    def side_effect_get_subnet_nacl_associations(self, subnets: list[str]):
        res = {}
        for subnet in subnets:

            n = re.findall(r"\d+", subnet)[0]
            res[f"test-subnet-nacl-association-id-{n}{subnet[-1:]}"] = (
                f"test-nacl-id-{n}"
            )
        return res

    ####################
    ### TEST METHODS ###
    ####################

    def test_disable_region_by_vpcs_blackhole_nacl(self):
        profile_name = "TestProfileName"
        test_region = "us-west-2"

        test_vpcs_in_region = [
            "test-vpc-id-1",
            "test-vpc-id-2",
        ]

        patch_parse_test_type_vpc = patch(
            "activities.vpc.actions.parse_test_target_type_vpc"
        )
        mock_parse_test_type_vpc = patch_parse_test_type_vpc.start()
        mock_parse_test_type_vpc.return_value = test_vpcs_in_region

        self.mock_boto3_client.return_value.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": f"test-subnet-id-1a", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-1b", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-2a", "VpcId": "test-vpc-id-2"},
                {"SubnetId": f"test-subnet-id-2b", "VpcId": "test-vpc-id-2"},
            ]
        }

        self.mock_associate_subnets_with_blackhole_nacls.return_value = {
            "test-subnet-blackhole-nacl-association-id-1a": "test-original-nacl-id-1",
            "test-subnet-blackhole-nacl-association-id-1b": "test-original-nacl-id-1",
            "test-subnet-blackhole-nacl-association-id-2a": "test-original-nacl-id-2",
            "test-subnet-blackhole-nacl-association-id-2b": "test-original-nacl-id-2",
        }

        response = disable_region_by_vpcs_blackhole_nacl(
            profile_name=profile_name,
            region=test_region,
            test_target_type="ID_LIST",
            targets=test_vpcs_in_region,
            state_file_name="",
        )

        self.assertEqual(
            self.mock_boto3_client.return_value.put_object.call_args.kwargs["Body"],
            json.dumps(
                {
                    "subnet_association_id_old_nacl_id_pairs": {
                        "test-subnet-blackhole-nacl-association-id-1a": "test-original-nacl-id-1",
                        "test-subnet-blackhole-nacl-association-id-1b": "test-original-nacl-id-1",
                        "test-subnet-blackhole-nacl-association-id-2a": "test-original-nacl-id-2",
                        "test-subnet-blackhole-nacl-association-id-2b": "test-original-nacl-id-2",
                    }
                }
            ),
        )

        patch_parse_test_type_vpc.stop()

    def test_disable_region_by_azs_blackhole_nacl(self):
        profile_name = "TestProfileName"
        test_region = "us-west-2"

        test_azs_in_region = [
            "test-az-id-1",
            "test-az-id-2",
        ]

        patch_parse_test_type_az = patch(
            "activities.vpc.actions.parse_test_target_type_az"
        )
        mock_parse_test_type_az = patch_parse_test_type_az.start()
        mock_parse_test_type_az.return_value = test_azs_in_region

        self.mock_boto3_client.return_value.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": f"test-subnet-id-1a", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-1b", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-2a", "VpcId": "test-vpc-id-2"},
                {"SubnetId": f"test-subnet-id-2b", "VpcId": "test-vpc-id-2"},
            ]
        }

        self.mock_associate_subnets_with_blackhole_nacls.return_value = {
            "test-subnet-blackhole-nacl-association-id-1a": "test-original-nacl-id-1",
            "test-subnet-blackhole-nacl-association-id-1b": "test-original-nacl-id-1",
            "test-subnet-blackhole-nacl-association-id-2a": "test-original-nacl-id-2",
            "test-subnet-blackhole-nacl-association-id-2b": "test-original-nacl-id-2",
        }

        response = disable_region_by_azs_blackhole_nacl(
            profile_name=profile_name,
            region=test_region,
            test_target_type="ID_LIST",
            targets=test_azs_in_region,
            state_file_name="",
        )

        self.assertEqual(
            self.mock_boto3_client.return_value.put_object.call_args.kwargs["Body"],
            json.dumps(
                {
                    "subnet_association_id_old_nacl_id_pairs": {
                        "test-subnet-blackhole-nacl-association-id-1a": "test-original-nacl-id-1",
                        "test-subnet-blackhole-nacl-association-id-1b": "test-original-nacl-id-1",
                        "test-subnet-blackhole-nacl-association-id-2a": "test-original-nacl-id-2",
                        "test-subnet-blackhole-nacl-association-id-2b": "test-original-nacl-id-2",
                    }
                },
            ),
        )

    def test_disable_region_by_subnets_blackhole_nacl(self):
        profile_name = "TestProfileName"
        test_region = "us-west-2"

        test_subnets_in_region = [
            "test-subnet-id-1",
            "test-subnet-id-2",
        ]

        patch_parse_test_type_subnet = patch(
            "activities.vpc.actions.parse_test_target_type_subnet"
        )
        mock_parse_test_type_az = patch_parse_test_type_subnet.start()
        mock_parse_test_type_az.return_value = test_subnets_in_region

        self.mock_boto3_client.return_value.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": f"test-subnet-id-1a", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-1b", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-2a", "VpcId": "test-vpc-id-2"},
                {"SubnetId": f"test-subnet-id-2b", "VpcId": "test-vpc-id-2"},
            ]
        }

        self.mock_associate_subnets_with_blackhole_nacls.return_value = {
            "test-subnet-blackhole-nacl-association-id-1a": "test-original-nacl-id-1",
            "test-subnet-blackhole-nacl-association-id-1b": "test-original-nacl-id-1",
            "test-subnet-blackhole-nacl-association-id-2a": "test-original-nacl-id-2",
            "test-subnet-blackhole-nacl-association-id-2b": "test-original-nacl-id-2",
        }

        response = disable_region_by_subnets_blackhole_nacl(
            profile_name=profile_name,
            region=test_region,
            test_target_type="ID_LIST",
            targets=test_subnets_in_region,
            state_file_name="",
        )

        self.assertEqual(
            self.mock_boto3_client.return_value.put_object.call_args.kwargs["Body"],
            json.dumps(
                {
                    "subnet_association_id_old_nacl_id_pairs": {
                        "test-subnet-blackhole-nacl-association-id-1a": "test-original-nacl-id-1",
                        "test-subnet-blackhole-nacl-association-id-1b": "test-original-nacl-id-1",
                        "test-subnet-blackhole-nacl-association-id-2a": "test-original-nacl-id-2",
                        "test-subnet-blackhole-nacl-association-id-2b": "test-original-nacl-id-2",
                    }
                },
            ),
        )

    def test_disable_region_by_vpcs_blackhole_route_table(self):
        profile_name = "TestProfileName"
        test_region = "us-west-2"

        test_vpcs_in_region = [
            "test-vpc-id-1",
            "test-vpc-id-2",
        ]

        patch_parse_test_type_vpc = patch(
            "activities.vpc.actions.parse_test_target_type_vpc"
        )
        mock_parse_test_type_vpc = patch_parse_test_type_vpc.start()
        mock_parse_test_type_vpc.return_value = test_vpcs_in_region

        self.mock_boto3_client.return_value.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": f"test-subnet-id-1a", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-1b", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-2a", "VpcId": "test-vpc-id-2"},
                {"SubnetId": f"test-subnet-id-2b", "VpcId": "test-vpc-id-2"},
            ]
        }

        self.mock_associate_subnets_with_blackhole_route_tables.return_value = {
            "test-subnet-blackhole-route-table-association-id-1a": "test-original-route-table-id-1",
            "test-subnet-blackhole-route-table-association-id-1b": "test-original-route-table-id-1",
            "test-subnet-blackhole-route-table-association-id-2a": "test-original-route-table-id-2",
            "test-subnet-blackhole-route-table-association-id-2b": "test-original-route-table-id-2",
        }

        response = disable_region_by_vpcs_blackhole_route_table(
            profile_name=profile_name,
            region=test_region,
            test_target_type="ID_LIST",
            targets=test_vpcs_in_region,
            state_file_name="",
        )

        self.assertEqual(
            self.mock_boto3_client.return_value.put_object.call_args.kwargs["Body"],
            json.dumps(
                {
                    "subnet_association_id_old_route_table_id_pairs": {
                        "test-subnet-blackhole-route-table-association-id-1a": "test-original-route-table-id-1",
                        "test-subnet-blackhole-route-table-association-id-1b": "test-original-route-table-id-1",
                        "test-subnet-blackhole-route-table-association-id-2a": "test-original-route-table-id-2",
                        "test-subnet-blackhole-route-table-association-id-2b": "test-original-route-table-id-2",
                    }
                }
            ),
        )

        patch_parse_test_type_vpc.stop()

    def test_disable_region_by_azs_blackhole_route_table(self):
        profile_name = "TestProfileName"
        test_region = "us-west-2"

        test_azs_in_region = [
            "test-az-id-1",
            "test-az-id-2",
        ]

        patch_parse_test_type_az = patch(
            "activities.vpc.actions.parse_test_target_type_az"
        )
        mock_parse_test_type_az = patch_parse_test_type_az.start()
        mock_parse_test_type_az.return_value = test_azs_in_region

        self.mock_boto3_client.return_value.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": f"test-subnet-id-1a", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-1b", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-2a", "VpcId": "test-vpc-id-2"},
                {"SubnetId": f"test-subnet-id-2b", "VpcId": "test-vpc-id-2"},
            ]
        }

        self.mock_associate_subnets_with_blackhole_route_tables.return_value = {
            "test-subnet-blackhole-route-table-association-id-1a": "test-original-route-table-id-1",
            "test-subnet-blackhole-route-table-association-id-1b": "test-original-route-table-id-1",
            "test-subnet-blackhole-route-table-association-id-2a": "test-original-route-table-id-2",
            "test-subnet-blackhole-route-table-association-id-2b": "test-original-route-table-id-2",
        }

        response = disable_region_by_azs_blackhole_route_table(
            profile_name=profile_name,
            region=test_region,
            test_target_type="ID_LIST",
            targets=test_azs_in_region,
            state_file_name="",
        )

        self.assertEqual(
            self.mock_boto3_client.return_value.put_object.call_args.kwargs["Body"],
            json.dumps(
                {
                    "subnet_association_id_old_route_table_id_pairs": {
                        "test-subnet-blackhole-route-table-association-id-1a": "test-original-route-table-id-1",
                        "test-subnet-blackhole-route-table-association-id-1b": "test-original-route-table-id-1",
                        "test-subnet-blackhole-route-table-association-id-2a": "test-original-route-table-id-2",
                        "test-subnet-blackhole-route-table-association-id-2b": "test-original-route-table-id-2",
                    }
                },
            ),
        )

    def test_disable_region_by_subnets_blackhole_route_table(self):
        profile_name = "TestProfileName"
        test_region = "us-west-2"

        test_subnets_in_region = [
            "test-subnet-id-1",
            "test-subnet-id-2",
        ]

        patch_parse_test_type_subnet = patch(
            "activities.vpc.actions.parse_test_target_type_subnet"
        )
        mock_parse_test_type_subnet = patch_parse_test_type_subnet.start()
        mock_parse_test_type_subnet.return_value = test_subnets_in_region

        self.mock_boto3_client.return_value.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": f"test-subnet-id-1a", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-1b", "VpcId": "test-vpc-id-1"},
                {"SubnetId": f"test-subnet-id-2a", "VpcId": "test-vpc-id-2"},
                {"SubnetId": f"test-subnet-id-2b", "VpcId": "test-vpc-id-2"},
            ]
        }

        self.mock_associate_subnets_with_blackhole_route_tables.return_value = {
            "test-subnet-blackhole-route-table-association-id-1a": "test-original-route-table-id-1",
            "test-subnet-blackhole-route-table-association-id-1b": "test-original-route-table-id-1",
            "test-subnet-blackhole-route-table-association-id-2a": "test-original-route-table-id-2",
            "test-subnet-blackhole-route-table-association-id-2b": "test-original-route-table-id-2",
        }

        response = disable_region_by_subnets_blackhole_route_table(
            profile_name=profile_name,
            region=test_region,
            test_target_type="ID_LIST",
            targets=test_subnets_in_region,
            state_file_name="",
        )

        self.assertEqual(
            self.mock_boto3_client.return_value.put_object.call_args.kwargs["Body"],
            json.dumps(
                {
                    "subnet_association_id_old_route_table_id_pairs": {
                        "test-subnet-blackhole-route-table-association-id-1a": "test-original-route-table-id-1",
                        "test-subnet-blackhole-route-table-association-id-1b": "test-original-route-table-id-1",
                        "test-subnet-blackhole-route-table-association-id-2a": "test-original-route-table-id-2",
                        "test-subnet-blackhole-route-table-association-id-2b": "test-original-route-table-id-2",
                    }
                },
            ),
        )


class TestReenableRegions(unittest.TestCase):
    ##################
    ### TEST SETUP ###
    ##################

    def setUp(self):
        self.mock_boto3_session = patch(
            "activities.vpc.actions.boto3.Session"
        ).start()

        self.mock_boto3_client = self.mock_boto3_session.return_value.client
        self.mock_boto3_client.get_object.return_value = Mock()

        self.mock_boto3_client.get_object.return_value.read.return_value = Mock()
        self.mock_boto3_client.get_object.return_value.read.return_value.decode.return_value = (
            Mock()
        )

        self.mock_json_loads = patch("activities.vpc.actions.json.loads").start()

        self.mock_logger = patch.object(activities.vpc.actions, "logger").start()

    def tearDown(self):
        patch.stopall()

    ####################
    ### SIDE EFFECTS ###
    ####################

    ####################
    ### TEST METHODS ###
    ####################

    def test_reenable_region_blackhole_nacl(self):
        profile_name = "TestProfileName"
        test_region = "us-west-2"

        self.mock_json_loads.return_value = {
            "subnet_association_id_old_nacl_id_pairs": {
                "test-subnet-blackhole-nacl-association-id-1a": "test-original-nacl-id-1",
                "test-subnet-blackhole-nacl-association-id-1b": "test-original-nacl-id-1",
                "test-subnet-blackhole-nacl-association-id-2a": "test-original-nacl-id-2",
                "test-subnet-blackhole-nacl-association-id-2b": "test-original-nacl-id-2",
            }
        }

        self.mock_boto3_client.return_value.describe_network_acls.return_value = {
            "NetworkAcls": [
                {
                    "NetworkAclId": "test-blackhole-nacl-id-1",
                },
                {
                    "NetworkAclId": "test-blackhole-nacl-id-2",
                },
            ]
        }

        reenable_region_blackhole_nacl(
            profile_name=profile_name, region=test_region, state_file_name=""
        )

        self.assertEqual(
            self.mock_boto3_client.return_value.replace_network_acl_association.call_args_list,
            [
                call(
                    AssociationId="test-subnet-blackhole-nacl-association-id-1a",
                    NetworkAclId="test-original-nacl-id-1",
                ),
                call(
                    AssociationId="test-subnet-blackhole-nacl-association-id-1b",
                    NetworkAclId="test-original-nacl-id-1",
                ),
                call(
                    AssociationId="test-subnet-blackhole-nacl-association-id-2a",
                    NetworkAclId="test-original-nacl-id-2",
                ),
                call(
                    AssociationId="test-subnet-blackhole-nacl-association-id-2b",
                    NetworkAclId="test-original-nacl-id-2",
                ),
            ],
        )

        self.assertEqual(
            self.mock_boto3_client.return_value.delete_network_acl.call_args_list,
            [
                call(NetworkAclId="test-blackhole-nacl-id-1"),
                call(NetworkAclId="test-blackhole-nacl-id-2"),
            ],
        )

    def test_reenable_region_blackhole_route_table(self):
        profile_name = "TestProfileName"
        test_region = "us-west-2"

        self.mock_json_loads.return_value = {
            "subnet_association_id_old_route_table_id_pairs": {
                "test-subnet-blackhole-route-table-association-id-1a": "test-original-route-table-id-1",
                "test-subnet-blackhole-route-table-association-id-1b": "test-original-route-table-id-1",
                "test-subnet-blackhole-route-table-association-id-2a": "test-original-route-table-id-2",
                "test-subnet-blackhole-route-table-association-id-2b": "test-original-route-table-id-2",
            }
        }

        self.mock_boto3_client.return_value.describe_route_tables.return_value = {
            "RouteTables": [
                {
                    "RouteTableId": "test-blackhole-route-table-id-1",
                },
                {
                    "RouteTableId": "test-blackhole-route-table-id-2",
                },
            ]
        }

        reenable_region_blackhole_route_table(
            profile_name=profile_name, region=test_region, state_file_name=""
        )

        self.assertEqual(
            self.mock_boto3_client.return_value.replace_route_table_association.call_args_list,
            [
                call(
                    AssociationId="test-subnet-blackhole-route-table-association-id-1a",
                    RouteTableId="test-original-route-table-id-1",
                ),
                call(
                    AssociationId="test-subnet-blackhole-route-table-association-id-1b",
                    RouteTableId="test-original-route-table-id-1",
                ),
                call(
                    AssociationId="test-subnet-blackhole-route-table-association-id-2a",
                    RouteTableId="test-original-route-table-id-2",
                ),
                call(
                    AssociationId="test-subnet-blackhole-route-table-association-id-2b",
                    RouteTableId="test-original-route-table-id-2",
                ),
            ],
        )

        self.assertEqual(
            self.mock_boto3_client.return_value.delete_route_table.call_args_list,
            [
                call(RouteTableId="test-blackhole-route-table-id-1"),
                call(RouteTableId="test-blackhole-route-table-id-2"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
