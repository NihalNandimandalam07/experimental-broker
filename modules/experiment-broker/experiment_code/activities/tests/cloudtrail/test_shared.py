import unittest
from unittest.mock import Mock, patch, call
from botocore.exceptions import ClientError
import datetime
import logging
import json
from pprint import pformat

import activities.cloudtrail.shared
from activities.cloudtrail.shared import (
    get_task_cloudtrail_events_by_resource_name,
    attempt_retry,
)

handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)
logger.addHandler(handler)


class TestShared(unittest.TestCase):
    def setUp(self):
        self.mock_logger = patch.object(
            activities.cloudtrail.shared, "logger"
        ).start()

        self.region = "test_region"

    def tearDown(self):
        patch.stopall()

    @patch("activities.ecs.shared.boto3.client")
    def test_get_task_cloudtrail_events_by_resource_name(self, mock_boto3_client):
        task_arn = "arn:aws:ecs:test_region:test_acc_id:task/test_cluster/test_task_id"
        mock_cloudtrail_client = Mock()

        mock_boto3_client.side_effect = [mock_cloudtrail_client]

        mock_cloudtrail_client.lookup_events.return_value = {"Events": []}

        resp = get_task_cloudtrail_events_by_resource_name(
            region=self.region, target=task_arn
        )

        assert resp == []


if __name__ == "__main__":
    unittest.main()
