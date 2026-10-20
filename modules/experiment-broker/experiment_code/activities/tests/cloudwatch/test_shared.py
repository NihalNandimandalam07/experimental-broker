import unittest
from unittest.mock import Mock, patch, call
from botocore.exceptions import ClientError

import logging
import json

handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

import activities.cloudwatch.shared
from activities.cloudwatch.shared import get_task_cloudwatch_logs


class TestShared(unittest.TestCase):

    def setUp(self):
        self.mock_logger = patch.object(
            activities.cloudwatch.shared, "logger"
        ).start()

        self.region = "test_region"

    def tearDown(self):
        patch.stopall()

    @patch("activities.ecs.shared.boto3.client")
    def test_get_task_cloudwatch_logs(self, mock_boto3_client):
        task_arn = "arn:aws:ecs:test_region:test_acc_id:task/test_cluster/test_task_id"
        mock_cloudtrail_client = Mock()
        mock_logs_client = Mock()
        mock_boto3_client.side_effect = [mock_cloudtrail_client, mock_logs_client]

        mock_cloudtrail_client.lookup_events.return_value = {
            "Events": [
                {
                    "EventName": "CreateLogStream",
                    "CloudTrailEvent": json.dumps(
                        {
                            "requestParameters": {
                                "logGroupName": "test_log_group_name",
                                "logStreamName": "test_log_stream_name",
                            }
                        }
                    ),
                }
            ]
        }
        mock_logs_client.get_log_events.return_value = {"events": ["event"]}
        resp = get_task_cloudwatch_logs(region=self.region, target=task_arn)

        assert resp == ["event"]


if __name__ == "__main__":
    unittest.main()
