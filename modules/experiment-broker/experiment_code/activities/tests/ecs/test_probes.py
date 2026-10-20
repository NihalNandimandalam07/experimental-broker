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

import activities.ecs.probes
from activities.ecs.probes import (
    assert_task_failed,
    assert_task_replaced,
    assert_tasks_disabled_network_inbound,
    assert_tasks_disabled_network_outbound,
    assert_tasks_remediated_network_inbound,
    assert_tasks_remediated_network_outbound,
    assert_task_definition_invalid_iam,
    assert_task_definition_remediated_iam,
    assert_task_definition_deregistered,
    assert_task_definition_deleted,
    assert_task_definition_remediated,
)


class TestProbes(unittest.TestCase):
    region = "test_region"
    cluster_name = "test_cluster"
    test_task_arn = "test_task_arn"
    test_task_definition_arn = "test_task_definition_arn"

    def setUp(self):
        self.mock_logger = patch.object(activities.ecs.probes, "logger").start()

    def tearDown(self):
        patch.stopall()

    def side_effect_attempt_retry(*args, **kwargs):
        if kwargs.get("retry") == False:
            raise AssertionError("Not retrying")
        if kwargs.get("current_iteration_time") >= kwargs.get(
            "max_duration_to_iterate"
        ):
            raise AssertionError("Max duration reached")

    @patch("activities.ecs.probes.get_task_status_by_arn")
    @patch("activities.ecs.probes.attempt_retry")
    def test_assert_task_failed_failure_no_retry(
        self,
        mock_attempt_retry,
        mock_get_task_status_by_arn,
    ):
        mock_get_task_status_by_arn.return_value = {"last_status": False}
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry
        with self.assertRaises(AssertionError):
            assert_task_failed(
                region=self.region,
                cluster_name=self.cluster_name,
                target=self.test_task_arn,
            )

        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.get_task_status_by_arn")
    @patch("activities.ecs.probes.attempt_retry")
    def test_assert_task_failed_failure_with_retry(
        self,
        mock_attempt_retry,
        mock_get_task_status_by_arn,
    ):
        mock_get_task_status_by_arn.return_value = {"last_status": False}
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry
        with self.assertRaises(AssertionError):
            assert_task_failed(
                region=self.region,
                cluster_name=self.cluster_name,
                target=self.test_task_arn,
                retry=True,
            )

        assert mock_attempt_retry.call_count == 5

    @patch("activities.ecs.probes.get_task_status_by_arn")
    @patch("activities.ecs.probes.attempt_retry")
    def test_assert_task_failed_success_no_retry(
        self,
        mock_attempt_retry,
        mock_get_task_status_by_arn,
    ):
        mock_get_task_status_by_arn.return_value = {"last_status": True}
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_failed(
            region=self.region,
            cluster_name=self.cluster_name,
            target=self.test_task_arn,
        )
        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.get_task_status_by_arn")
    @patch("activities.ecs.probes.attempt_retry")
    def test_assert_task_failed_success_with_retry(
        self,
        mock_attempt_retry,
        mock_get_task_status_by_arn,
    ):
        mock_get_task_status_by_arn.return_value = {"last_status": True}
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_failed(
            region=self.region,
            cluster_name=self.cluster_name,
            target=self.test_task_arn,
            retry=True,
        )
        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.get_task_status_by_arn")
    @patch("activities.ecs.probes.attempt_retry")
    def test_assert_task_failed_eventual_success(
        self,
        mock_attempt_retry,
        mock_get_task_status_by_arn,
    ):
        mock_get_task_status_by_arn.side_effect = [
            {"last_status": False},
            {"last_status": True},
        ]
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_failed(
            region=self.region,
            cluster_name=self.cluster_name,
            target=self.test_task_arn,
            retry=True,
        )
        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_replaced_failure_no_valid_target_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.list_tasks.return_value = {"taskArns": []}
        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                    "tags": [{"key": "UnitTest", "value": "True"}],
                    "stoppedAt": 1,
                }
            ]
        }
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_replaced(
                region=self.region,
                cluster_name=self.cluster_name,
                target=self.test_task_arn,
            )

        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_replaced_failure_no_valid_target_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.list_tasks.return_value = {"taskArns": []}
        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                    "tags": [{"key": "UnitTest", "value": "True"}],
                    "stoppedAt": 1,
                }
            ]
        }
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_replaced(
                region=self.region,
                cluster_name=self.cluster_name,
                target=self.test_task_arn,
                retry=True,
            )

        assert mock_attempt_retry.call_count == 5

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_replaced_failure_valid_target_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.list_tasks.return_value = {"taskArns": ["test_task_arn"]}
        mock_ecs_client.describe_tasks.side_effect = [
            {
                "tasks": [
                    {
                        "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                        "tags": [{"key": "UnitTest", "value": "True"}],
                        "stoppedAt": 1,
                    }
                ]
            },
            {
                "tasks": [
                    {
                        "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                        "tags": [{"key": "UnitTest", "value": "True"}],
                        "createdAt": 0,
                    },
                ]
            },
        ]
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_replaced(
                region=self.region,
                cluster_name=self.cluster_name,
                target=self.test_task_arn,
            )

        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_replaced_failure_valid_target_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        def side_effect_describe_tasks(*args, **kwargs):
            if kwargs.get("tasks")[0] == "test_task_arn":
                return {
                    "tasks": [
                        {
                            "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                            "tags": [{"key": "UnitTest", "value": "True"}],
                            "stoppedAt": 1,
                        }
                    ]
                }
            else:
                return {
                    "tasks": [
                        {
                            "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                            "tags": [{"key": "UnitTest", "value": "True"}],
                            "createdAt": 0,
                        },
                    ]
                }

        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.list_tasks.return_value = {
            "taskArns": ["test_not_target_task_arn"]
        }
        mock_ecs_client.describe_tasks.side_effect = side_effect_describe_tasks

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_replaced(
                region=self.region,
                cluster_name=self.cluster_name,
                target=self.test_task_arn,
                retry=True,
            )

        assert mock_attempt_retry.call_count == 5

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_replaced_success_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        def side_effect_describe_tasks(*args, **kwargs):
            if kwargs.get("tasks")[0] == "test_task_arn":
                return {
                    "tasks": [
                        {
                            "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                            "tags": [{"key": "UnitTest", "value": "True"}],
                            "stoppedAt": 1,
                        }
                    ]
                }
            else:
                return {
                    "tasks": [
                        {
                            "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                            "tags": [{"key": "UnitTest", "value": "True"}],
                            "createdAt": 2,
                        },
                    ]
                }

        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.list_tasks.return_value = {
            "taskArns": ["test_not_target_task_arn"]
        }
        mock_ecs_client.describe_tasks.side_effect = side_effect_describe_tasks
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_replaced(
            region=self.region,
            cluster_name=self.cluster_name,
            target=self.test_task_arn,
        )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_replaced_success_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        def side_effect_describe_tasks(*args, **kwargs):
            if kwargs.get("tasks")[0] == "test_task_arn":
                return {
                    "tasks": [
                        {
                            "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                            "tags": [{"key": "UnitTest", "value": "True"}],
                            "stoppedAt": 1,
                        }
                    ]
                }
            else:
                return {
                    "tasks": [
                        {
                            "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                            "tags": [{"key": "UnitTest", "value": "True"}],
                            "createdAt": 2,
                        },
                    ]
                }

        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.list_tasks.return_value = {
            "taskArns": ["test_not_target_task_arn"]
        }
        mock_ecs_client.describe_tasks.side_effect = side_effect_describe_tasks
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_replaced(
            region=self.region,
            cluster_name=self.cluster_name,
            target=self.test_task_arn,
            retry=True,
        )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_replaced_eventual_success(
        self, mock_boto3_client, mock_attempt_retry
    ):

        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.list_tasks.return_value = {
            "taskArns": ["test_not_target_task_arn"]
        }
        mock_ecs_client.describe_tasks.side_effect = [
            {
                "tasks": [
                    {
                        "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                        "tags": [{"key": "UnitTest", "value": "True"}],
                        "stoppedAt": 1,
                    }
                ]
            },
            {
                "tasks": [
                    {
                        "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                        "tags": [{"key": "UnitTest", "value": "True"}],
                        "createdAt": 0,
                    },
                ]
            },
            {
                "tasks": [
                    {
                        "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                        "tags": [{"key": "UnitTest", "value": "True"}],
                        "createdAt": 2,
                    },
                ]
            },
        ]
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_replaced(
            region=self.region,
            cluster_name=self.cluster_name,
            target=self.test_task_arn,
            retry=True,
        )

        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_replaced_eventual_success_filtering_tags(
        self, mock_boto3_client, mock_attempt_retry
    ):

        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.list_tasks.return_value = {
            "taskArns": ["test_not_target_task_arn"]
        }
        mock_ecs_client.describe_tasks.side_effect = [
            {
                "tasks": [
                    {
                        "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                        "tags": [{"key": "UnitTest", "value": "True"}],
                        "stoppedAt": 1,
                    }
                ]
            },
            {
                "tasks": [
                    {
                        "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                        "tags": [{"key": "UnitTest", "value": "False"}],
                        "createdAt": 2,
                    },
                ]
            },
            {
                "tasks": [
                    {
                        "taskDefinitionArn": "arn:aws:ecs:test_region:test_account_id:test_family/test-task-definition:test_revision",
                        "tags": [{"key": "UnitTest", "value": "True"}],
                        "createdAt": 2,
                    },
                ]
            },
        ]
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_replaced(
            region=self.region,
            cluster_name=self.cluster_name,
            target=self.test_task_arn,
            tag_key="UnitTest",
            tag_value="True",
            retry=True,
        )

        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_invalid_iam_failure_no_retry(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client, mock_iam_client]

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry
        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskRoleArn": "arn:aws:iam::test_acc_id:role/test_role_name"
            }
        }
        mock_iam_client.list_role_policies.return_value = {
            "PolicyNames": ["invoke_failure"]
        }
        mock_iam_client.list_attached_role_policies.return_value = {
            "AttachedPolicies": ["invoke_failure"]
        }

        with self.assertRaises(AssertionError):
            assert_task_definition_invalid_iam(
                region=self.region,
                target=self.test_task_definition_arn,
            )

        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_invalid_iam_failure_with_retry(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client, mock_iam_client]

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry
        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskRoleArn": "arn:aws:iam::test_acc_id:role/test_role_name"
            }
        }
        mock_iam_client.list_role_policies.return_value = {
            "PolicyNames": ["invoke_failure"]
        }
        mock_iam_client.list_attached_role_policies.return_value = {
            "AttachedPolicies": ["invoke_failure"]
        }

        with self.assertRaises(AssertionError):
            assert_task_definition_invalid_iam(
                region=self.region,
                target=self.test_task_definition_arn,
                retry=True,
            )

        assert mock_attempt_retry.call_count == 3

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_invalid_iam_success_no_retry(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client, mock_iam_client]

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry
        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskRoleArn": "arn:aws:iam::test_acc_id:role/test_role_name"
            }
        }
        mock_iam_client.list_role_policies.return_value = {"PolicyNames": []}
        mock_iam_client.list_attached_role_policies.return_value = {
            "AttachedPolicies": []
        }

        assert_task_definition_invalid_iam(
            region=self.region,
            target=self.test_task_definition_arn,
        )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_invalid_iam_success_with_retry(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client, mock_iam_client]

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry
        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskRoleArn": "arn:aws:iam::test_acc_id:role/test_role_name"
            }
        }
        mock_iam_client.list_role_policies.return_value = {"PolicyNames": []}
        mock_iam_client.list_attached_role_policies.return_value = {
            "AttachedPolicies": []
        }

        assert_task_definition_invalid_iam(
            region=self.region,
            target=self.test_task_definition_arn,
            retry=True,
        )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_iam_failure_no_rollback(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        mock_s3_client = Mock()
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [
            mock_s3_client,
            mock_ecs_client,
            mock_iam_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = "{}"

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated_iam(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_iam_failure_role_does_not_exist(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        mock_s3_client = Mock()
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [
            mock_s3_client,
            mock_ecs_client,
            mock_iam_client,
        ]

        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskRoleArn": "arn:aws:iam::test_acc_id:role/invalid_role_name"
            }
        }

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = (
            '{"test_role_name": "test_role_name"}'
        )

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated_iam(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_iam_failure_role_not_attached(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        mock_s3_client = Mock()
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [
            mock_s3_client,
            mock_ecs_client,
            mock_iam_client,
        ]

        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskRoleArn": "arn:aws:iam::test_acc_id:role/invalid_role_name"
            }
        }

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = (
            '{"test_role_name": "test_role_name"}'
        )

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated_iam(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_iam_failure_inline_policy_no_retry(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        test_role_name = "test_role_name"

        mock_s3_client = Mock()
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [
            mock_s3_client,
            mock_ecs_client,
            mock_iam_client,
        ]

        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskRoleArn": f"arn:aws:iam::test_acc_id:role/{test_role_name}"
            }
        }

        mock_iam_client.list_role_policies.return_value = {
            "PolicyNames": ["invoke_failure"]
        }

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = f'{{"{test_role_name}": {{"inline_policies": [{{"test_inline_policy_name":"test_policy"}}]}}}}'

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated_iam(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_iam_failure_inline_policy_with_retry(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        test_role_name = "test_role_name"

        mock_s3_client = Mock()
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [
            mock_s3_client,
            mock_ecs_client,
            mock_iam_client,
        ]

        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskRoleArn": f"arn:aws:iam::test_acc_id:role/{test_role_name}"
            }
        }

        mock_iam_client.list_role_policies.return_value = {
            "PolicyNames": ["invoke_failure"]
        }

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = f'{{"{test_role_name}": {{"inline_policies": [{{"test_inline_policy_name":"test_policy"}}]}}}}'

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated_iam(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
                retry=True,
            )

        assert mock_attempt_retry.call_count == 3
        self.assertTrue(
            f"assert_task_definition_remediated_iam - Inline policies ['test_inline_policy_name'] are not attached to role {test_role_name}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_iam_failure_managed_policy_no_retry(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        test_role_name = "test_role_name"

        mock_s3_client = Mock()
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [
            mock_s3_client,
            mock_ecs_client,
            mock_iam_client,
        ]

        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskRoleArn": f"arn:aws:iam::test_acc_id:role/{test_role_name}"
            }
        }

        mock_iam_client.list_role_policies.return_value = {
            "PolicyNames": ["test_inline_policy_name"]
        }
        mock_iam_client.list_attached_role_policies.return_value = {
            "AttachedPolicies": [{"PolicyName": "invoke_failure"}]
        }

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = f'{{"{test_role_name}": {{"managed_policies": [{{"PolicyName":"test_managed_policy_name"}}],"inline_policies": [{{"test_inline_policy_name":"test_policy"}}]}}}}'

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated_iam(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_task_definition_remediated_iam - Managed policies ['test_managed_policy_name'] are not attached to role {test_role_name}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_iam_success_no_retry(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        test_role_name = "test_role_name"

        mock_s3_client = Mock()
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [
            mock_s3_client,
            mock_ecs_client,
            mock_iam_client,
        ]

        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskRoleArn": f"arn:aws:iam::test_acc_id:role/{test_role_name}"
            }
        }

        mock_iam_client.list_role_policies.return_value = {
            "PolicyNames": ["test_inline_policy_name"]
        }
        mock_iam_client.list_attached_role_policies.return_value = {
            "AttachedPolicies": [{"PolicyName": "test_managed_policy_name"}]
        }

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = f'{{"{test_role_name}": {{"managed_policies": [{{"PolicyName":"test_managed_policy_name"}}],"inline_policies": [{{"test_inline_policy_name":"test_policy"}}]}}}}'

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_definition_remediated_iam(
            region=self.region,
            target=self.test_task_definition_arn,
            rollback_file_name="test_rollback.json",
        )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_iam_success_with_retry(
        self,
        mock_boto3_client,
        mock_attempt_retry,
    ):
        test_role_name = "test_role_name"

        mock_s3_client = Mock()
        mock_ecs_client = Mock()
        mock_iam_client = Mock()

        mock_boto3_client.side_effect = [
            mock_s3_client,
            mock_ecs_client,
            mock_iam_client,
        ]

        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskRoleArn": f"arn:aws:iam::test_acc_id:role/{test_role_name}"
            }
        }

        mock_iam_client.list_role_policies.return_value = {
            "PolicyNames": ["test_inline_policy_name"]
        }
        mock_iam_client.list_attached_role_policies.side_effect = [
            {"AttachedPolicies": [{"PolicyName": "invoke_error"}]},
            {"AttachedPolicies": [{"PolicyName": "test_managed_policy_name"}]},
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = f'{{"{test_role_name}": {{"managed_policies": [{{"PolicyName":"test_managed_policy_name"}}],"inline_policies": [{{"test_inline_policy_name":"test_policy"}}]}}}}'

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_definition_remediated_iam(
            region=self.region,
            target=self.test_task_definition_arn,
            rollback_file_name="test_rollback.json",
            retry=True,
        )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_task_definition_remediated_iam - Managed policies ['test_managed_policy_name'] are not attached to role {test_role_name}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_disable_network_inbound_failure_eni_not_attached(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_ec2_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client, mock_ec2_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [{"taskArn": "err_task", "attachments": [{"type": "error"}]}]
        }

        with self.assertRaises(AssertionError):
            assert_tasks_disabled_network_inbound(
                region=self.region,
                cluster_name=self.cluster_name,
                targets=[self.test_task_definition_arn],
            )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_disable_network_inbound_failure_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_boto3_client.side_effect = [mock_ecs_client, mock_ec2_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "err_task",
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {
                                    "name": "networkInterfaceId",
                                    "value": "test_interface",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [{"Groups": [{"GroupId": "test_group_id"}]}]
        }

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {"GroupId": "test_group_id", "IpPermissions": [{"IpProtocol": "tcp"}]}
            ]
        }

        with self.assertRaises(AssertionError):
            assert_tasks_disabled_network_inbound(
                region=self.region,
                cluster_name=self.cluster_name,
                targets=[self.test_task_definition_arn],
            )

        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_disable_network_inbound_failure_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_boto3_client.side_effect = [mock_ecs_client, mock_ec2_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "err_task",
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {
                                    "name": "networkInterfaceId",
                                    "value": "test_interface",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [{"Groups": [{"GroupId": "test_group_id"}]}]
        }

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {"GroupId": "test_group_id", "IpPermissions": [{"IpProtocol": "tcp"}]}
            ]
        }

        with self.assertRaises(AssertionError):
            assert_tasks_disabled_network_inbound(
                region=self.region,
                cluster_name=self.cluster_name,
                targets=[self.test_task_definition_arn],
                retry=True,
            )

        assert mock_attempt_retry.call_count == 3

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_disable_network_inbound_success_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_boto3_client.side_effect = [mock_ecs_client, mock_ec2_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "err_task",
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {
                                    "name": "networkInterfaceId",
                                    "value": "test_interface",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [{"Groups": [{"GroupId": "test_group_id"}]}]
        }

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [{"GroupId": "test_group_id", "IpPermissions": []}]
        }

        assert_tasks_disabled_network_inbound(
            region=self.region,
            cluster_name=self.cluster_name,
            targets=[self.test_task_definition_arn],
        )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_disable_network_inbound_success_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_boto3_client.side_effect = [mock_ecs_client, mock_ec2_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "err_task",
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {
                                    "name": "networkInterfaceId",
                                    "value": "test_interface",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [{"Groups": [{"GroupId": "test_group_id"}]}]
        }

        mock_ec2_client.describe_security_groups.side_effect = [
            {
                "SecurityGroups": [
                    {
                        "GroupId": "test_group_id",
                        "IpPermissions": [{"IpProtocol": "tcp"}],
                    }
                ],
            },
            {
                "SecurityGroups": [{"GroupId": "test_group_id", "IpPermissions": []}],
            },
        ]

        assert_tasks_disabled_network_inbound(
            region=self.region,
            cluster_name=self.cluster_name,
            targets=[self.test_task_definition_arn],
            retry=True,
        )

        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_disable_network_outbound_failure_eni_not_attached(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_ec2_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client, mock_ec2_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [{"taskArn": "err_task", "attachments": [{"type": "error"}]}]
        }

        with self.assertRaises(AssertionError):
            assert_tasks_disabled_network_outbound(
                region=self.region,
                cluster_name=self.cluster_name,
                targets=[self.test_task_definition_arn],
            )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_disable_network_outbound_failure_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_boto3_client.side_effect = [mock_ecs_client, mock_ec2_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "err_task",
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {
                                    "name": "networkInterfaceId",
                                    "value": "test_interface",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [{"Groups": [{"GroupId": "test_group_id"}]}]
        }

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {
                    "GroupId": "test_group_id",
                    "IpPermissionsEgress": [{"IpProtocol": "tcp"}],
                }
            ]
        }

        with self.assertRaises(AssertionError):
            assert_tasks_disabled_network_outbound(
                region=self.region,
                cluster_name=self.cluster_name,
                targets=[self.test_task_definition_arn],
            )

        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_disable_network_outbound_failure_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_boto3_client.side_effect = [mock_ecs_client, mock_ec2_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "err_task",
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {
                                    "name": "networkInterfaceId",
                                    "value": "test_interface",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [{"Groups": [{"GroupId": "test_group_id"}]}]
        }

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {
                    "GroupId": "test_group_id",
                    "IpPermissionsEgress": [{"IpProtocol": "tcp"}],
                }
            ]
        }

        with self.assertRaises(AssertionError):
            assert_tasks_disabled_network_outbound(
                region=self.region,
                cluster_name=self.cluster_name,
                targets=[self.test_task_definition_arn],
                retry=True,
            )

        assert mock_attempt_retry.call_count == 3

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_disable_network_outbound_success_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_boto3_client.side_effect = [mock_ecs_client, mock_ec2_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "err_task",
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {
                                    "name": "networkInterfaceId",
                                    "value": "test_interface",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [{"Groups": [{"GroupId": "test_group_id"}]}]
        }

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [{"GroupId": "test_group_id", "IpPermissionsEgress": []}]
        }

        assert_tasks_disabled_network_outbound(
            region=self.region,
            cluster_name=self.cluster_name,
            targets=[self.test_task_definition_arn],
        )

        assert mock_attempt_retry.call_count == 0

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_disable_network_outbound_success_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_boto3_client.side_effect = [mock_ecs_client, mock_ec2_client]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "err_task",
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {
                                    "name": "networkInterfaceId",
                                    "value": "test_interface",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [{"Groups": [{"GroupId": "test_group_id"}]}]
        }

        mock_ec2_client.describe_security_groups.side_effect = [
            {
                "SecurityGroups": [
                    {
                        "GroupId": "test_group_id",
                        "IpPermissionsEgress": [{"IpProtocol": "tcp"}],
                    }
                ],
            },
            {
                "SecurityGroups": [
                    {"GroupId": "test_group_id", "IpPermissionsEgress": []}
                ],
            },
        ]

        assert_tasks_disabled_network_outbound(
            region=self.region,
            cluster_name=self.cluster_name,
            targets=[self.test_task_definition_arn],
            retry=True,
        )

        assert mock_attempt_retry.call_count == 1

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_tasks_remediated_network_inbound_failure_no_rollback_file(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps({})

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_tasks_remediated_network_inbound(
                region=self.region,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 0
        self.assertTrue(
            "assert_tasks_remediated_network_inbound - Rollback config empty."
            in [call.args[0] for call in self.mock_logger.error.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_tasks_remediated_network_inbound_failure_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {"test_group_id": [{"port": 80}]}
        )

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {"GroupId": "test_group_id", "IpPermissions": [{"IpProtocol": "tcp"}]}
            ]
        }

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_tasks_remediated_network_inbound(
                region=self.region,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_tasks_remediated_network_inbound - Failed asserting Task network inbound remediation for security groups ['test_group_id']."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_tasks_remediated_network_inbound_failure_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {"test_group_id": [{"port": 80}]}
        )

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {"GroupId": "test_group_id", "IpPermissions": [{"IpProtocol": "tcp"}]}
            ]
        }

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_tasks_remediated_network_inbound(
                region=self.region, rollback_file_name="test_rollback.json", retry=True
            )

        assert mock_attempt_retry.call_count == 3
        self.assertTrue(
            f"assert_tasks_remediated_network_inbound - Failed asserting Task network inbound remediation for security groups ['test_group_id']."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_tasks_remediated_network_inbound_success_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {"test_group_id": [{"IpProtocol": "tcp"}]}
        )

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {"GroupId": "test_group_id", "IpPermissions": [{"IpProtocol": "tcp"}]}
            ]
        }

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_tasks_remediated_network_inbound(
            region=self.region,
            rollback_file_name="test_rollback.json",
        )

        assert mock_attempt_retry.call_count == 0
        self.assertTrue(
            "Succeeded asserting network inbound remediated from rollback."
            in [call.args[0] for call in self.mock_logger.info.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_tasks_remediated_network_inbound_success_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {"test_group_id": [{"IpProtocol": "tcp"}]}
        )

        mock_ec2_client.describe_security_groups.side_effect = [
            {
                "SecurityGroups": [
                    {
                        "GroupId": "test_group_id",
                        "IpPermissions": [{"none": "none"}],
                    }
                ]
            },
            {
                "SecurityGroups": [
                    {
                        "GroupId": "test_group_id",
                        "IpPermissions": [{"IpProtocol": "tcp"}],
                    }
                ]
            },
        ]

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_tasks_remediated_network_inbound(
            region=self.region, rollback_file_name="test_rollback.json", retry=True
        )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_tasks_remediated_network_inbound - Failed asserting Task network inbound remediation for security groups ['test_group_id']."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )
        self.assertTrue(
            "Succeeded asserting network inbound remediated from rollback."
            in [call.args[0] for call in self.mock_logger.info.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_tasks_remediated_network_outbound_failure_no_rollback_file(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps({})

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_tasks_remediated_network_outbound(
                region=self.region,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 0
        self.assertTrue(
            "assert_tasks_remediated_network_outbound - Rollback config empty."
            in [call.args[0] for call in self.mock_logger.error.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_tasks_remediated_network_outbound_failure_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {"test_group_id": [{"port": 80}]}
        )

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {
                    "GroupId": "test_group_id",
                    "IpPermissionsEgress": [{"IpProtocol": "tcp"}],
                }
            ]
        }

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_tasks_remediated_network_outbound(
                region=self.region,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_tasks_remediated_network_outbound - Failed asserting Task network outbound remediation for security groups ['test_group_id']."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_tasks_remediated_network_outbound_failure_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {"test_group_id": [{"port": 80}]}
        )

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {
                    "GroupId": "test_group_id",
                    "IpPermissionsEgress": [{"IpProtocol": "tcp"}],
                }
            ]
        }

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_tasks_remediated_network_outbound(
                region=self.region, rollback_file_name="test_rollback.json", retry=True
            )

        assert mock_attempt_retry.call_count == 3
        self.assertTrue(
            f"assert_tasks_remediated_network_outbound - Failed asserting Task network outbound remediation for security groups ['test_group_id']."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_tasks_remediated_network_outbound_success_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {"test_group_id": [{"IpProtocol": "tcp"}]}
        )

        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {
                    "GroupId": "test_group_id",
                    "IpPermissionsEgress": [{"IpProtocol": "tcp"}],
                }
            ]
        }

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_tasks_remediated_network_outbound(
            region=self.region,
            rollback_file_name="test_rollback.json",
        )

        assert mock_attempt_retry.call_count == 0
        self.assertTrue(
            "Succeeded asserting network outbound remediated from rollback."
            in [call.args[0] for call in self.mock_logger.info.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_tasks_remediated_network_outbound_success_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {"test_group_id": [{"IpProtocol": "tcp"}]}
        )

        mock_ec2_client.describe_security_groups.side_effect = [
            {
                "SecurityGroups": [
                    {
                        "GroupId": "test_group_id",
                        "IpPermissionsEgress": [{"none": "none"}],
                    }
                ]
            },
            {
                "SecurityGroups": [
                    {
                        "GroupId": "test_group_id",
                        "IpPermissionsEgress": [{"IpProtocol": "tcp"}],
                    }
                ]
            },
        ]

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_tasks_remediated_network_outbound(
            region=self.region, rollback_file_name="test_rollback.json", retry=True
        )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_tasks_remediated_network_outbound - Failed asserting Task network outbound remediation for security groups ['test_group_id']."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )
        self.assertTrue(
            "Succeeded asserting network outbound remediated from rollback."
            in [call.args[0] for call in self.mock_logger.info.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_deleted_failure_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_ecs_client.describe_task_definition.return_value = []
        with self.assertRaises(AssertionError):
            assert_task_definition_deleted(
                region=self.region,
                target=self.test_task_definition_arn,
            )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_task_definition_deleted - Task definition {self.test_task_definition_arn} still exists in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_deleted_failure_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_ecs_client.describe_task_definition.return_value = []
        with self.assertRaises(AssertionError):
            assert_task_definition_deleted(
                region=self.region, target=self.test_task_definition_arn, retry=True
            )

        assert mock_attempt_retry.call_count == 3
        self.assertTrue(
            f"assert_task_definition_deleted - Task definition {self.test_task_definition_arn} still exists in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_deleted_success_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_ecs_client.describe_task_definition.side_effect = ClientError({}, {})
        assert_task_definition_deleted(
            region=self.region, target=self.test_task_definition_arn
        )

        assert mock_attempt_retry.call_count == 0
        self.assertTrue(
            f"assert_task_definition_deleted - Assertion Success. Task definition {self.test_task_definition_arn} has been deleted in region {self.region}."
            in [call.args[0] for call in self.mock_logger.info.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_deleted_success_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()

        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_ecs_client.describe_task_definition.side_effect = [[], ClientError({}, {})]
        assert_task_definition_deleted(
            region=self.region, target=self.test_task_definition_arn, retry=True
        )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_task_definition_deleted - Task definition {self.test_task_definition_arn} still exists in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )
        self.assertTrue(
            f"assert_task_definition_deleted - Assertion Success. Task definition {self.test_task_definition_arn} has been deleted in region {self.region}."
            in [call.args[0] for call in self.mock_logger.info.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_deregistered_task_definition_does_not_exist(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.describe_task_definition.side_effect = ClientError({}, {})

        with self.assertRaises(AssertionError):
            assert_task_definition_deregistered(
                region=self.region, target=self.test_task_definition_arn
            )
        self.assertTrue(
            f"Task definition {self.test_task_definition_arn} does not exist in region {self.region}."
            in [call.args[0] for call in self.mock_logger.error.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_deregistered_failure_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.describe_task_definition.side_effect = [
            {"taskDefinition": {"status": "ACTIVE"}}
        ]

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_deregistered(
                region=self.region, target=self.test_task_definition_arn
            )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_task_definition_deregistered - Task definition {self.test_task_definition_arn} is still active in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_deregistered_failure_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {"status": "ACTIVE"}
        }

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_deregistered(
                region=self.region, target=self.test_task_definition_arn, retry=True
            )

        assert mock_attempt_retry.call_count == 3
        self.assertTrue(
            f"assert_task_definition_deregistered - Task definition {self.test_task_definition_arn} is still active in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_deregistered_success_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {"status": "STOPPED"}
        }

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_definition_deregistered(
            region=self.region, target=self.test_task_definition_arn
        )

        assert mock_attempt_retry.call_count == 0
        self.assertTrue(
            f"assert_task_definition_deregistered - Assertion Success. Task definition {self.test_task_definition_arn} has been deregistered in region {self.region}."
            in [call.args[0] for call in self.mock_logger.info.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_deregistered_success_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_boto3_client.side_effect = [mock_ecs_client]
        mock_ecs_client.describe_task_definition.side_effect = [
            {"taskDefinition": {"status": "ACTIVE"}},
            {"taskDefinition": {"status": "STOPPED"}},
        ]

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_definition_deregistered(
            region=self.region, target=self.test_task_definition_arn, retry=True
        )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_task_definition_deregistered - Task definition {self.test_task_definition_arn} is still active in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )
        self.assertTrue(
            f"assert_task_definition_deregistered - Assertion Success. Task definition {self.test_task_definition_arn} has been deregistered in region {self.region}."
            in [call.args[0] for call in self.mock_logger.info.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_rollback_failure_no_rollback(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps({})

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 0
        self.assertTrue(
            "assert_task_definition_remediated - Rollback config empty."
            in [call.args[0] for call in self.mock_logger.error.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_rollback_failure_target_not_in_rollback(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {"invalid_task_definition_arn": {}}
        )

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 0
        self.assertTrue(
            f"assert_task_definition_remediated - Task definition {self.test_task_definition_arn} not found in rollback config."
            in [call.args[0] for call in self.mock_logger.error.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_rollback_failure_task_definition_does_not_exist_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {self.test_task_definition_arn: {}}
        )

        mock_ecs_client.describe_task_definition.side_effect = ClientError({}, {})

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_task_definition_remediated - Task definition {self.test_task_definition_arn} not found in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_rollback_failure_task_definition_does_not_exist_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {self.test_task_definition_arn: {}}
        )

        mock_ecs_client.describe_task_definition.side_effect = ClientError({}, {})

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
                retry=True,
            )

        assert mock_attempt_retry.call_count == 3
        self.assertTrue(
            f"assert_task_definition_remediated - Task definition {self.test_task_definition_arn} not found in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_rollback_failure_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {self.test_task_definition_arn: {}}
        )

        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {"status": "DEREGISTERED"}
        }

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
            )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_task_definition_remediated - Task definition {self.test_task_definition_arn} is not ACTIVE in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_rollback_failure_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {self.test_task_definition_arn: {}}
        )

        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {"status": "DEREGISTERED"}
        }

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        with self.assertRaises(AssertionError):
            assert_task_definition_remediated(
                region=self.region,
                target=self.test_task_definition_arn,
                rollback_file_name="test_rollback.json",
                retry=True,
            )

        assert mock_attempt_retry.call_count == 3
        self.assertTrue(
            f"assert_task_definition_remediated - Task definition {self.test_task_definition_arn} is not ACTIVE in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_rollback_success_no_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {self.test_task_definition_arn: {}}
        )

        mock_ecs_client.describe_task_definition.return_value = {
            "taskDefinition": {"status": "ACTIVE"}
        }

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_definition_remediated(
            region=self.region,
            target=self.test_task_definition_arn,
            rollback_file_name="test_rollback.json",
        )

        assert mock_attempt_retry.call_count == 0
        self.assertTrue(
            f"assert_task_definition_remediated - Assertion Success. Task definition {self.test_task_definition_arn} is ACTIVE in region {self.region}."
            in [call.args[0] for call in self.mock_logger.info.call_args_list]
        )

    @patch("activities.ecs.probes.attempt_retry")
    @patch("activities.ecs.probes.boto3.client")
    def test_assert_task_definition_remediated_rollback_success_with_retry(
        self, mock_boto3_client, mock_attempt_retry
    ):
        mock_ecs_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_s3_client,
        ]

        mock_body = Mock()

        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_body.read.return_value.decode.return_value = json.dumps(
            {self.test_task_definition_arn: {}}
        )

        mock_ecs_client.describe_task_definition.side_effect = [
            {"taskDefinition": {"status": "DEREGISTERED"}},
            {"taskDefinition": {"status": "ACTIVE"}},
        ]

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        assert_task_definition_remediated(
            region=self.region,
            target=self.test_task_definition_arn,
            rollback_file_name="test_rollback.json",
            retry=True,
        )

        assert mock_attempt_retry.call_count == 1
        self.assertTrue(
            f"assert_task_definition_remediated - Task definition {self.test_task_definition_arn} is not ACTIVE in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )
        self.assertTrue(
            f"assert_task_definition_remediated - Task definition {self.test_task_definition_arn} is not ACTIVE in region {self.region}."
            in [call.kwargs["error_log"] for call in mock_attempt_retry.call_args_list]
        )


if __name__ == "__main__":
    unittest.main()
