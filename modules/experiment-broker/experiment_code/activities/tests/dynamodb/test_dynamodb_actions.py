import unittest
from unittest.mock import Mock, patch

from activities.dynamodb.actions import blackhole_dynamodb


class TestDynamoDBActions(unittest.TestCase):
    @patch("activities.dynamodb.actions.boto3")
    def test_blackhole_dynamo(self, mock_boto3):
        blackhole_dynamodb("Name", ["node1", "node2"])

        mock_boto3.Session().client().send_command.assert_called_with(
            Targets=[{"Key": "Name", "Values": ["node1", "node2"]}],
            DocumentName="BlackHoleDynamoStress",
            Parameters={"Key": ["duration"], "Value": ["2"]},
        )
