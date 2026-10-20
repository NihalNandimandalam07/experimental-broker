import unittest
from unittest.mock import Mock, patch, call
from botocore.exceptions import ClientError
import datetime
import logging
import json
from pprint import pformat

handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

import activities.ecs.shared
from activities.ecs.shared import (
    attempt_retry,
    get_task_arns_by_tag,
    get_task_definition_arns_by_tag,
    get_task_status_by_arn,
    handle_test_target_type,
)


class TestShared(unittest.TestCase):

    cluster_name = "test_cluster"
    region = "test_region"
    tag_key = "test_tag_key"
    tag_value = "test_tag_value"

    def setUp(self):
        self.mock_logger = patch.object(activities.ecs.shared, "logger").start()

    def tearDown(self):
        patch.stopall()

    @patch("activities.ecs.shared.time.sleep")
    def test_attempt_retry_no_retry(self, mock_time_sleep):

        error_log = "test_error"

        with self.assertRaises(AssertionError):
            attempt_retry(
                error_log=error_log,
                retry=False,
                current_iteration_time=0,
                max_duration_to_iterate=30,
                sleep_duration=15,
            )
        self.mock_logger.error.assert_called_once_with(error_log)

    @patch("activities.ecs.shared.time.sleep")
    def test_attempt_retry_exceeded_max_duration(self, mock_time_sleep):

        error_log = "test_error"

        with self.assertRaises(AssertionError):
            attempt_retry(
                error_log=error_log,
                retry=True,
                current_iteration_time=15,
                max_duration_to_iterate=0,
                sleep_duration=15,
            )
        self.mock_logger.error.assert_called_once_with(error_log)

    @patch("activities.ecs.shared.time.sleep")
    def test_attempt_retry_exceeded_max_duration(self, mock_time_sleep):

        error_log = "test_error"

        attempt_retry(
            error_log=error_log,
            retry=True,
            current_iteration_time=0,
            max_duration_to_iterate=30,
            sleep_duration=15,
        )

        self.mock_logger.error.assert_called_once_with(error_log)
        self.mock_logger.info.call_count == 2
        mock_time_sleep.call_count == 1

    @patch("activities.ecs.shared.boto3.client")
    def test_get_task_arns_by_tag_no_tasks_with_tag(
        self,
        mock_boto3_client,
    ):

        mock_ecs_client = Mock()
        mock_boto3_client.side_effect = [mock_ecs_client]

        mock_ecs_client.list_tasks.return_value = {"taskArns": ["test_task_arn"]}

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [{"tags": [{"key": "wrong_key", "value": "wrong_value"}]}]
        }

        resp = get_task_arns_by_tag(
            cluster_name=self.cluster_name,
            region=self.region,
            tag_key=self.tag_key,
            tag_value=self.tag_value,
        )

        assert resp == []

        self.assertTrue(
            f'Cluster {self.cluster_name} does not contain any tasks with tag "{self.tag_key}:{self.tag_value}"'
            in [call.args[0] for call in self.mock_logger.info.call_args_list]
        )

    @patch("activities.ecs.shared.boto3.client")
    def test_get_task_arns_by_tag_success_both_task_statuses(
        self,
        mock_boto3_client,
    ):

        mock_ecs_client = Mock()
        mock_boto3_client.side_effect = [mock_ecs_client]

        mock_ecs_client.list_tasks.return_value = {"taskArns": ["test_task_arn"]}

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "test_task_arn_1",
                    "tags": [{"key": self.tag_key, "value": self.tag_value}],
                },
                {
                    "taskArn": "test_task_arn_2",
                    "tags": [{"key": self.tag_key, "value": self.tag_value}],
                },
            ]
        }

        resp = get_task_arns_by_tag(
            cluster_name=self.cluster_name,
            region=self.region,
            tag_key=self.tag_key,
            tag_value=self.tag_value,
        )

        assert mock_ecs_client.describe_tasks.call_args_list[0].kwargs.get(
            "tasks", []
        ) == [
            "test_task_arn",
            "test_task_arn",
        ]

        self.assertTrue(resp == ["test_task_arn_1", "test_task_arn_2"])

    @patch("activities.ecs.shared.boto3.client")
    def test_get_task_definition_arns_by_tag_no_task_definitions(
        self, mock_boto3_client
    ):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]

        mock_ecs_client.list_task_definitions.return_value = {"taskDefinitionArns": []}

        resp = get_task_definition_arns_by_tag(
            region=self.region, tag_key=self.tag_key, tag_value=self.tag_value
        )

        assert resp == []

        self.assertTrue(
            f"Region {self.region} does not contain any task definitions with tag '{self.tag_key}:{self.tag_value}'"
        )

    @patch("activities.ecs.shared.boto3.client")
    def test_get_task_definition_arns_by_tag_success(self, mock_boto3_client):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]

        mock_ecs_client.list_task_definitions.return_value = {
            "taskDefinitionArns": ["test_tag_definition_arn"]
        }

        mock_ecs_client.list_tags_for_resource.return_value = {
            "tags": [{"key": self.tag_key, "value": self.tag_value}]
        }

        resp = get_task_definition_arns_by_tag(
            region=self.region, tag_key=self.tag_key, tag_value=self.tag_value
        )

        assert resp == ["test_tag_definition_arn"]

    @patch("activities.ecs.shared.boto3.client")
    def test_get_task_status_by_arn_no_status(self, mock_boto3_client):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]

        resp = get_task_status_by_arn(
            region=self.region, cluster_name=self.cluster_name, target="test_task_arn"
        )

        assert resp == {}

    @patch("activities.ecs.shared.boto3.client")
    def test_get_task_status_by_arn_desired_status(self, mock_boto3_client):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [{"lastStatus": "ACTIVE", "desiredStatus": "ACTIVE"}]
        }

        resp = get_task_status_by_arn(
            region=self.region,
            cluster_name=self.cluster_name,
            target="test_task_arn",
            desired_status="ACTIVE",
        )

        assert resp == {"desired_status": True}

    @patch("activities.ecs.shared.boto3.client")
    def test_get_task_status_by_arn_last_status(self, mock_boto3_client):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [{"lastStatus": "ACTIVE", "desiredStatus": "ACTIVE"}]
        }

        resp = get_task_status_by_arn(
            region=self.region,
            cluster_name=self.cluster_name,
            target="test_task_arn",
            last_status="STOPPED",
        )

        assert resp == {"last_status": False}

    @patch("activities.ecs.shared.boto3.client")
    def test_get_task_status_by_arn_both_statuses(self, mock_boto3_client):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [{"lastStatus": "ACTIVE", "desiredStatus": "ACTIVE"}]
        }

        resp = get_task_status_by_arn(
            region=self.region,
            cluster_name=self.cluster_name,
            target="test_task_arn",
            desired_status="STOPPED",
            last_status="ACTIVE",
        )

        assert resp == {"desired_status": False, "last_status": True}

    def test_handle_test_target_type_invalid_target_type(self):

        targets = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        with self.assertRaises(ValueError):
            resp = handle_test_target_type(test_target_type="INVALID", targets=targets)

    def test_handle_test_target_type_all(self):
        targets = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        resp = handle_test_target_type(test_target_type="ALL", targets=targets)

        assert resp == targets

    def test_handle_test_target_type_random(self):
        targets = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        resp = handle_test_target_type(test_target_type="RANDOM", targets=targets)

        assert set(resp).issubset(set(targets))


if __name__ == "__main__":
    unittest.main()
