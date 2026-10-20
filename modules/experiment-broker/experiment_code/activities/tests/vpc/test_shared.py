import unittest

from botocore.exceptions import ClientError
from unittest.mock import Mock, patch, call
import logging

logging.basicConfig(level=logging.INFO)

import activities.vpc.shared
from activities.vpc.shared import (
    parse_test_target_type_vpc,
    parse_test_target_type_az,
    parse_test_target_type_subnet,
    associate_subnets_with_blackhole_nacls,
    associate_subnets_with_blackhole_route_tables,
    create_blackhole_nacl_in_vpc,
    create_blackhole_route_table_in_vpc,
)


class TestVpcParsing(unittest.TestCase):
    available_vpc_id_response = {
        "Vpcs": [
            {
                "VpcId": "test-vpc-id-1",
            },
            {
                "VpcId": "test-vpc-id-2",
            },
            {
                "VpcId": "test-vpc-id-3",
            },
            {
                "VpcId": "test-vpc-id-4",
            },
        ]
    }

    def setUp(self):
        self.mock_ec2_client = Mock()
        self.mock_ec2_client.describe_vpcs.return_value = self.available_vpc_id_response
        self.mock_logger = patch.object(activities.vpc.shared, "logger").start()

    def tearDown(self):
        patch.stopall()

    def test_parse_test_target_type_vpc_random(self):
        assert all(
            [
                vpc_id
                in [vpc["VpcId"] for vpc in self.available_vpc_id_response["Vpcs"]]
                for vpc_id in parse_test_target_type_vpc(
                    "RANDOM", [], ec2_client=self.mock_ec2_client
                )
            ]
        )

    def test_parse_test_target_type_vpc_id_list(self):
        test_id_list = ["test-vpc-id-1", "test-vpc-id-2"]
        assert (
            parse_test_target_type_vpc(
                "ID_LIST", test_id_list, ec2_client=self.mock_ec2_client
            )
            == test_id_list
        )

        invalid_test_id_list = ["invalid-vpc-id-1"]

        with self.assertRaises(ValueError):
            parse_test_target_type_vpc(
                "ID_LIST", invalid_test_id_list, ec2_client=self.mock_ec2_client
            )

    def test_parse_test_target_type_vpc_all(self):
        assert parse_test_target_type_vpc(
            "ALL", [], ec2_client=self.mock_ec2_client
        ) == [vpc["VpcId"] for vpc in self.available_vpc_id_response["Vpcs"]]

    def test_parse_test_target_type_vpc_invalid_type(self):
        with self.assertRaises(ValueError):
            parse_test_target_type_vpc("INVALID", [], ec2_client=self.mock_ec2_client)


class TestAzParsing(unittest.TestCase):
    available_az_id_response = {
        "AvailabilityZones": [
            {
                "ZoneId": "test-az-id-1",
            },
            {
                "ZoneId": "test-az-id-2",
            },
            {
                "ZoneId": "test-az-id-3",
            },
            {
                "ZoneId": "test-az-id-4",
            },
        ]
    }

    def setUp(self):
        self.mock_ec2_client = Mock()
        self.mock_ec2_client.describe_availability_zones.return_value = (
            self.available_az_id_response
        )
        self.mock_logger = patch.object(activities.vpc.shared, "logger").start()

    def tearDown(self):
        patch.stopall()

    def test_parse_test_target_type_az_random(self):
        assert all(
            [
                az_id
                in [
                    az["ZoneId"]
                    for az in self.available_az_id_response["AvailabilityZones"]
                ]
                for az_id in parse_test_target_type_az(
                    "RANDOM", [], ec2_client=self.mock_ec2_client
                )
            ]
        )

    def test_parse_test_target_type_az_id_list(self):
        test_id_list = ["test-az-id-1", "test-az-id-2"]
        assert (
            parse_test_target_type_az(
                "ID_LIST", test_id_list, ec2_client=self.mock_ec2_client
            )
            == test_id_list
        )

        invalid_test_id_list = ["invalid-az-id-1"]

        with self.assertRaises(ValueError):
            parse_test_target_type_az(
                "ID_LIST", invalid_test_id_list, ec2_client=self.mock_ec2_client
            )

    def test_parse_test_target_type_az_all(self):
        assert parse_test_target_type_az(
            "ALL", [], ec2_client=self.mock_ec2_client
        ) == [az["ZoneId"] for az in self.available_az_id_response["AvailabilityZones"]]

    def test_parse_test_target_type_az_invalid_type(self):
        with self.assertRaises(ValueError):
            parse_test_target_type_az("INVALID", [], ec2_client=self.mock_ec2_client)


class TestSubnetParsing(unittest.TestCase):
    available_subnet_id_response = {
        "Subnets": [
            {
                "SubnetId": "test-subnet-id-1",
            },
            {
                "SubnetId": "test-subnet-id-2",
            },
            {
                "SubnetId": "test-subnet-id-3",
            },
            {
                "SubnetId": "test-subnet-id-4",
            },
        ]
    }

    def setUp(self):
        self.mock_ec2_client = Mock()
        self.mock_ec2_client.describe_subnets.return_value = (
            self.available_subnet_id_response
        )

    def test_parse_test_target_type_subnet_random(self):
        assert all(
            [
                subnet_id
                in [
                    subnet["SubnetId"]
                    for subnet in self.available_subnet_id_response["Subnets"]
                ]
                for subnet_id in parse_test_target_type_subnet(
                    "RANDOM", [], ec2_client=self.mock_ec2_client
                )
            ]
        )

    def test_parse_test_target_type_subnet_id_list(self):
        test_id_list = ["test-subnet-id-1", "test-subnet-id-2"]
        assert (
            parse_test_target_type_subnet(
                "ID_LIST", test_id_list, ec2_client=self.mock_ec2_client
            )
            == test_id_list
        )

        invalid_test_id_list = ["invalid-subnet-id-1"]

        with self.assertRaises(ValueError):
            parse_test_target_type_subnet(
                "ID_LIST", invalid_test_id_list, ec2_client=self.mock_ec2_client
            )

    def test_parse_test_target_type_subnet_all(self):
        assert parse_test_target_type_subnet(
            "ALL", [], ec2_client=self.mock_ec2_client
        ) == [
            subnet["SubnetId"]
            for subnet in self.available_subnet_id_response["Subnets"]
        ]

    def test_parse_test_target_type_subnet_invalid_type(self):
        with self.assertRaises(ValueError):
            parse_test_target_type_subnet(
                "INVALID", [], ec2_client=self.mock_ec2_client
            )


class TestCreateBlackholes(unittest.TestCase):
    def setUp(self):
        self.mock_ec2_client = Mock()
        self.mock_logger = patch.object(activities.vpc.shared, "logger").start()

    def tearDown(self):
        patch.stopall()

    def test_create_blackhole_nacl_in_vpc(self):
        test_nacl_id = "test-nacl-id"

        self.mock_ec2_client.create_network_acl.return_value = {
            "NetworkAcl": {"NetworkAclId": test_nacl_id}
        }

        nacl_id = create_blackhole_nacl_in_vpc("test-vpc-id", self.mock_ec2_client)
        self.assertEqual(
            self.mock_ec2_client.create_network_acl_entry.call_args_list[0],
            call(
                CidrBlock="0.0.0.0/0",
                Egress=True,
                PortRange={"From": 0, "To": 65535},
                NetworkAclId=nacl_id,
                Protocol="-1",
                RuleAction="deny",
                RuleNumber=100,
            ),
        )

        self.assertEqual(
            self.mock_ec2_client.create_network_acl_entry.call_args_list[1],
            call(
                CidrBlock="0.0.0.0/0",
                Egress=False,
                PortRange={"From": 0, "To": 65535},
                NetworkAclId=nacl_id,
                Protocol="-1",
                RuleAction="deny",
                RuleNumber=100,
            ),
        )
        assert nacl_id == test_nacl_id

    def test_create_blackhole_route_table_in_vpc(self):
        test_route_table_id = "test-route-table-id"

        self.mock_ec2_client.create_route_table.return_value = {
            "RouteTable": {"RouteTableId": test_route_table_id}
        }

        route_table_id = create_blackhole_route_table_in_vpc(
            "test-vpc-id", self.mock_ec2_client
        )

        assert route_table_id == test_route_table_id


class TestGetters(unittest.TestCase):
    def setUp(self):
        self.mock_ec2_client = Mock()
        self.mock_logger = patch.object(activities.vpc.shared, "logger").start()

    def tearDown(self):
        patch.stopall()

    def test_get_nacl_association_ids_by_subnets(self):
        test_subnets = ["test-subnet-id-1", "test-subnet-id-2"]

        self.mock_ec2_client.describe_network_acls.return_value = {
            "NetworkAcls": [
                {
                    "Associations": [
                        {
                            "NetworkAclAssociationId": "test-association-id-1",
                            "SubnetId": "test-subnet-id-1",
                            "NetworkAclId": "test-nacl-id-1",
                        }
                    ]
                },
                {
                    "Associations": [
                        {
                            "NetworkAclAssociationId": "test-association-id-2",
                            "SubnetId": "test-subnet-id-2",
                            "NetworkAclId": "test-nacl-id-2",
                        }
                    ]
                },
            ]
        }

        nacl_association_ids = (
            activities.vpc.shared.get_nacl_association_ids_by_subnets(
                subnet_ids=test_subnets, ec2_client=self.mock_ec2_client
            )
        )

        assert nacl_association_ids == {
            "test-subnet-id-1": {
                "NetworkAclAssociationId": "test-association-id-1",
                "NetworkAclId": "test-nacl-id-1",
            },
            "test-subnet-id-2": {
                "NetworkAclAssociationId": "test-association-id-2",
                "NetworkAclId": "test-nacl-id-2",
            },
        }

    def test_get_route_table_association_ids_by_subnets(self):
        test_subnets = ["test-subnet-id-1", "test-subnet-id-2"]

        self.mock_ec2_client.describe_route_tables.return_value = {
            "RouteTables": [
                {
                    "Associations": [
                        {
                            "RouteTableAssociationId": "test-association-id-1",
                            "SubnetId": "test-subnet-id-1",
                            "RouteTableId": "test-route-table-id-1",
                        }
                    ]
                },
                {
                    "Associations": [
                        {
                            "RouteTableAssociationId": "test-association-id-2",
                            "SubnetId": "test-subnet-id-2",
                            "RouteTableId": "test-route-table-id-2",
                        }
                    ]
                },
            ]
        }

        route_table_association_ids = (
            activities.vpc.shared.get_route_table_association_ids_by_subnets(
                subnet_ids=test_subnets, ec2_client=self.mock_ec2_client
            )
        )

        assert route_table_association_ids == {
            "test-subnet-id-1": {
                "RouteTableAssociationId": "test-association-id-1",
                "RouteTableId": "test-route-table-id-1",
            },
            "test-subnet-id-2": {
                "RouteTableAssociationId": "test-association-id-2",
                "RouteTableId": "test-route-table-id-2",
            },
        }


class TestAssociateBlackhole(unittest.TestCase):
    def setUp(self):
        self.mock_ec2_client = Mock()
        self.mock_logger = patch.object(activities.vpc.shared, "logger").start()

    def tearDown(self):
        patch.stopall()

    def test_associate_subnets_with_blackhole_nacls(self):
        test_subnets = [
            {"SubnetId": "test-subnet-id-1", "VpcId": "test-vpc-id"},
            {"SubnetId": "test-subnet-id-2", "VpcId": "test-vpc-id"},
        ]
        test_vpc_id_blackhole_nacl_id_pairs = {"test-vpc-id": "test-blackhole-nacl-id"}

        patcher_get_nacl_association_ids_by_subnets = patch(
            "activities.vpc.shared.get_nacl_association_ids_by_subnets"
        )
        mock_get_nacl_association_ids_by_subnets = (
            patcher_get_nacl_association_ids_by_subnets.start()
        )
        mock_get_nacl_association_ids_by_subnets.return_value = {
            "test-subnet-id-1": {
                "NetworkAclAssociationId": "test-association-id-1",
                "NetworkAclId": "test-nacl-id-1",
            },
            "test-subnet-id-2": {
                "NetworkAclAssociationId": "test-association-id-2",
                "NetworkAclId": "test-nacl-id-2",
            },
        }

        self.mock_ec2_client.replace_network_acl_association.return_value = {
            "NewAssociationId": "test-new-association-id"
        }

        associate_subnets_with_blackhole_nacls(
            subnets=test_subnets,
            vpc_id_blackhole_nacl_id_pairs=test_vpc_id_blackhole_nacl_id_pairs,
            ec2_client=self.mock_ec2_client,
        )

        self.assertEqual(
            self.mock_ec2_client.replace_network_acl_association.call_args_list,
            [
                call(
                    AssociationId="test-association-id-1",
                    NetworkAclId="test-blackhole-nacl-id",
                ),
                call(
                    AssociationId="test-association-id-2",
                    NetworkAclId="test-blackhole-nacl-id",
                ),
            ],
        )

        patcher_get_nacl_association_ids_by_subnets.stop()

    def test_associate_subnets_with_blackhole_route_tables(self):
        test_subnets = [
            {"SubnetId": "test-subnet-id-1", "VpcId": "test-vpc-id"},
            {"SubnetId": "test-subnet-id-2", "VpcId": "test-vpc-id"},
        ]
        test_vpc_id_blackhole_route_table_id_pairs = {
            "test-vpc-id": "test-blackhole-route-table-id"
        }

        patcher_get_route_table_association_ids_by_subnets = patch(
            "activities.vpc.shared.get_route_table_association_ids_by_subnets"
        )
        mock_get_route_table_association_ids_by_subnets = (
            patcher_get_route_table_association_ids_by_subnets.start()
        )
        mock_get_route_table_association_ids_by_subnets.return_value = {
            "test-subnet-id-1": {
                "RouteTableAssociationId": "test-association-id-1",
                "RouteTableId": "test-route-table-id-1",
            },
            "test-subnet-id-2": {
                "RouteTableAssociationId": "test-association-id-2",
                "RouteTableId": "test-route-table-id-2",
            },
        }

        self.mock_ec2_client.replace_route_table_association.return_value = {
            "NewAssociationId": "test-new-association-id"
        }

        associate_subnets_with_blackhole_route_tables(
            subnets=test_subnets,
            vpc_id_blackhole_route_table_id_pairs=test_vpc_id_blackhole_route_table_id_pairs,
            ec2_client=self.mock_ec2_client,
        )

        self.assertEqual(
            self.mock_ec2_client.replace_route_table_association.call_args_list,
            [
                call(
                    AssociationId="test-association-id-1",
                    RouteTableId="test-blackhole-route-table-id",
                ),
                call(
                    AssociationId="test-association-id-2",
                    RouteTableId="test-blackhole-route-table-id",
                ),
            ],
        )

        patcher_get_route_table_association_ids_by_subnets.stop()


if __name__ == "__main__":
    unittest.main()
