import unittest
from unittest.mock import Mock, patch

from activities.kafka.actions import blackhole_kafka


class TestKafkaActions(unittest.TestCase):
    @patch("activities.kafka.actions.get_broker_endpoints")
    @patch("activities.kafka.actions.boto3")
    def test_blackhole_kafka(self, mock_boto3, mock_endpoints):
        blackhole_kafka("kafka-cluster", "NodeName", ["node1", "node2"])

        mock_endpoints.assert_called_with("kafka-cluster")
        kafkanodes = mock_endpoints.return_value

        mock_boto3.Session().client().send_command.assert_called_with(
            DocumentName="BlackHoleKafka",
            Targets=[{"Key": "NodeName", "Values": ["node1", "node2"]}],
            Parameters={"kafkanodes": [kafkanodes]},
            TimeoutSeconds=120,
            DocumentVersion="1",
            MaxErrors="10",
            MaxConcurrency="1",
        )
