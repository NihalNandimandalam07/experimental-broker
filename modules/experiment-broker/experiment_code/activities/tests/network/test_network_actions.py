import unittest
from unittest.mock import Mock, patch

from activities.network.actions import point_inactive_dns


class TestNetworkActions(unittest.TestCase):
    @patch("activities.network.actions.boto3")
    def test_point_inactive_dns(self, mock_boto3):
        point_inactive_dns("Name", ["node1", "node2"])

        mock_boto3.Session().client().send_command.assert_called_with(
            Targets=[{"Key": "Name", "Values": ["node1", "node2"]}],
            DocumentName=["BlackHoleDNS"],
        )
