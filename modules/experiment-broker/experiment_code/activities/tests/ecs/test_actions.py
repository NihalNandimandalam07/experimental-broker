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

import activities.ecs.actions
from activities.ecs.actions import (
    S3_BUCKET_NAME,
    datetime_handler,
    halt_tasks_execution,
    disable_tasks_by_network_inbound,
    disable_tasks_by_network_outbound,
    disable_tasks_by_deregister_task_definition,
    disable_tasks_by_delete_task_definition,
    rollback_disable_tasks_by_task_definition,
    rollback_disable_tasks_by_network_inbound,
    rollback_disable_tasks_by_network_outbound,
    disable_task_definitions_by_invalid_iam,
    rollback_disable_task_definitions_by_invalid_iam,
)


class TestDisableTasks(unittest.TestCase):
    def setUp(self):
        self.region = "test_region"
        self.cluster = "test_cluster"
        self.test_target_type = "ALL"

        self.test_target_task_arns = ["test_task_arn_1", "test_task_arn_2"]
        self.test_target_task_definition_arns = [
            "test_task_definition_arn_1",
            "test_task_definition_arn_2",
        ]

        self.mock_logger = patch.object(activities.ecs.actions, "logger").start()

    def tearDown(self):
        patch.stopall()

    ################
    # SIDE EFFECTS #
    ################

    def side_effect_boto3_deregister_task_definition_success(*args, **kwargs):
        return {
            "taskDefinition": {
                "taskDefinitionArn": kwargs.get("taskDefinition"),
                "revision": "test_revision",
                "status": "test_status",
                "requiresAttributes": [],
                "compatibilities": [],
                "registeredAt": "test_registered_at",
                "registeredBy": "test_registered_by",
                "otherField": "test_other_field",
            },
            "failures": [],
        }

    def side_effect_boto3_deregister_task_definition_failure(*args, **kwargs):
        return {
            "taskDefinition": {
                "taskDefinitionArn": kwargs.get("taskDefinition"),
                "revision": "test_revision",
                "status": "test_status",
                "requiresAttributes": [],
                "compatibilities": [],
                "registeredAt": "test_registered_at",
                "registeredBy": "test_registered_by",
                "otherField": "test_other_field",
            },
            "failures": [
                {"arn": kwargs.get("taskDefinition"), "reason": "test failure"}
            ],
        }

    def side_effect_disable_tasks_by_deregister_task_definition_success(
        *args, **kwargs
    ):
        return {target: True for target in kwargs.get("targets")}

    def side_effect_disable_tasks_by_deregister_task_definition_failure(
        *args, **kwargs
    ):
        return {target: False for target in kwargs.get("targets")}

    ################
    # TEST METHODS #
    ################

    def test_datetime_handler_with_datetime(self):
        dt = datetime.datetime(2022, 12, 31, 23, 59, 59)
        self.assertEqual(datetime_handler(dt), "2022-12-31T23:59:59")

    def test_datetime_handler_with_non_datetime(self):
        with self.assertRaises(TypeError):
            datetime_handler("not a datetime")

    @patch("activities.ecs.actions.time.sleep")
    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_halt_tasks_execution_max_retries_reached(
        self, mock_handle_test_target_type, mock_boto3_client, mock_time_sleep
    ):

        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_boto3_client.return_value.stop_task.return_value = {}

        mock_boto3_client.return_value.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": self.test_target_task_arns[0],
                    "lastStatus": "WRONG",
                },
                {
                    "taskArn": self.test_target_task_arns[1],
                    "lastStatus": "STOPPED",
                },
            ]
        }

        halt_tasks_execution(
            region=self.region,
            cluster_name=self.cluster,
            test_target_type="ALL",
            targets=self.test_target_task_arns,
            reason="Stopped by Experiment Broker.",
        )

        mock_boto3_client.return_value.stop_task.assert_any_call(
            cluster=self.cluster,
            task=self.test_target_task_arns[0],
            reason="Stopped by Experiment Broker.",
        )
        mock_boto3_client.return_value.stop_task.assert_any_call(
            cluster=self.cluster,
            task=self.test_target_task_arns[1],
            reason="Stopped by Experiment Broker.",
        )

        self.mock_logger.warning.assert_called()

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_halt_tasks_execution_success_no_retry(
        self, mock_handle_test_target_type, mock_boto3_client
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_ecs_client = Mock()
        mock_s3_client = Mock()

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_boto3_client.side_effect = [mock_ecs_client, mock_s3_client]

        mock_ecs_client.describe_tasks.side_effect = [
            {
                "tasks": [
                    {
                        "taskArn": self.test_target_task_arns[0],
                        "lastStatus": "STOPPED",
                    },
                    {
                        "taskArn": self.test_target_task_arns[1],
                        "lastStatus": "STOPPED",
                    },
                ]
            }
        ]

        halt_tasks_execution(
            region=self.region,
            cluster_name=self.cluster,
            test_target_type="ALL",
            targets=self.test_target_task_arns,
            reason="Stopped by Experiment Broker.",
        )

        mock_ecs_client.stop_task.assert_any_call(
            cluster=self.cluster,
            task=self.test_target_task_arns[0],
            reason="Stopped by Experiment Broker.",
        )
        mock_ecs_client.stop_task.assert_any_call(
            cluster=self.cluster,
            task=self.test_target_task_arns[1],
            reason="Stopped by Experiment Broker.",
        )

        self.mock_logger.info.assert_any_call(
            "halt_tasks_execution - All tasks have stopped."
        )
        self.assertFalse(self.mock_logger.info.any_call == "Sleeping for 15 seconds...")

        assert self.mock_logger.warning.call_count == 0

    @patch("activities.ecs.actions.time.sleep")
    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_halt_tasks_execution_eventual_success(
        self, mock_handle_test_target_type, mock_boto3_client, mock_time_sleep
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_ecs_client = Mock()
        mock_s3_client = Mock()

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_boto3_client.side_effect = [mock_ecs_client, mock_s3_client]

        mock_ecs_client.describe_tasks.side_effect = [
            {
                "tasks": [
                    {
                        "taskArn": self.test_target_task_arns[0],
                        "lastStatus": "WRONG",
                    },
                    {
                        "taskArn": self.test_target_task_arns[1],
                        "lastStatus": "STOPPED",
                    },
                ]
            },
            {
                "tasks": [
                    {
                        "taskArn": self.test_target_task_arns[0],
                        "lastStatus": "STOPPED",
                        "stoppedAt": None,
                    },
                    {
                        "taskArn": self.test_target_task_arns[1],
                        "lastStatus": "STOPPED",
                        "stoppedAt": None,
                    },
                ]
            },
        ]

        halt_tasks_execution(
            region=self.region,
            cluster_name=self.cluster,
            test_target_type="ALL",
            targets=self.test_target_task_arns,
            reason="Stopped by Experiment Broker.",
        )

        mock_ecs_client.stop_task.assert_any_call(
            cluster=self.cluster,
            task=self.test_target_task_arns[0],
            reason="Stopped by Experiment Broker.",
        )
        mock_ecs_client.stop_task.assert_any_call(
            cluster=self.cluster,
            task=self.test_target_task_arns[1],
            reason="Stopped by Experiment Broker.",
        )

        self.mock_logger.info.assert_any_call("Sleeping for 15 seconds...")

        self.mock_logger.info.assert_any_call(
            "halt_tasks_execution - All tasks have stopped."
        )

        mock_s3_client.put_object.assert_called_once()

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_halt_tasks_execution_exceptions(
        self, mock_handle_test_target_type, mock_boto3_client
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_boto3_client.return_value.stop_task.side_effect = ClientError(
            {"Error": {"Code": "400", "Message": "Bad Request"}}, "StopTask"
        )

        halt_tasks_execution(
            region=self.region,
            cluster_name=self.cluster,
            test_target_type="ALL",
            targets=self.test_target_task_arns,
        )
        self.mock_logger.error.assert_called_with(
            pformat(
                "halt_tasks_execution - (ClientError): An error occurred (400) when calling the StopTask operation: Bad Request"
            )
        )

        mock_boto3_client.return_value.stop_task.side_effect = Exception(
            "Test Exception"
        )

        halt_tasks_execution(
            region=self.region,
            cluster_name=self.cluster,
            test_target_type="ALL",
            targets=self.test_target_task_arns,
        )

        self.mock_logger.error.assert_called_with(
            pformat(
                "halt_tasks_execution - (Exception) An unexpected error occurred: Test Exception"
            )
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.json.dumps")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_disable_tasks_by_deregister_task_definition_success(
        self, mock_handle_test_target_type, mock_json_dumps, mock_boto3_client
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_boto3_client.return_value.deregister_task_definition.side_effect = (
            self.side_effect_boto3_deregister_task_definition_success
        )

        disable_tasks_by_deregister_task_definition(
            region=self.region,
            test_target_type=self.test_target_type,
            targets=self.test_target_task_definition_arns,
        )

        mock_json_dumps.return_value = json.dumps(
            {
                "test_task_definition_arn_1": {
                    "otherField": "test_other_field",
                },
                "test_task_definition_arn_2": {
                    "otherField": "test_other_field",
                },
            }
        )

        mock_boto3_client.return_value.deregister_task_definition.assert_has_calls(
            [
                call(taskDefinition="test_task_definition_arn_1"),
                call(taskDefinition="test_task_definition_arn_2"),
            ]
        )

        mock_boto3_client.return_value.put_object.assert_has_calls(
            [
                call(
                    Bucket=S3_BUCKET_NAME,
                    Key="disable_task_definitions_by_deregister.json",
                    Body=json.dumps(
                        {
                            "test_task_definition_arn_1": {
                                "otherField": "test_other_field",
                            },
                            "test_task_definition_arn_2": {
                                "otherField": "test_other_field",
                            },
                        }
                    ),
                ),
            ]
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_disable_tasks_by_deregister_task_definition_failure(
        self, mock_handle_test_target_type, mock_boto3_client
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_boto3_client.return_value.deregister_task_definition.side_effect = (
            self.side_effect_boto3_deregister_task_definition_failure
        )

        disable_tasks_by_deregister_task_definition(
            region=self.region,
            test_target_type=self.test_target_type,
            targets=self.test_target_task_definition_arns,
        )

        mock_boto3_client.return_value.deregister_task_definition.assert_has_calls(
            [
                call(taskDefinition="test_task_definition_arn_1"),
            ]
        )

        mock_boto3_client.return_value.put_object.assert_has_calls(
            [
                call(
                    Bucket=S3_BUCKET_NAME,
                    Key="disable_task_definitions_by_deregister.json",
                    Body=json.dumps({}),
                ),
            ]
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_disable_tasks_by_deregister_task_definition_exceptions(
        self, mock_handle_test_target_type, mock_boto3_client
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_boto3_client.return_value.deregister_task_definition.side_effect = (
            Exception("Test Exception")
        )
        disable_tasks_by_deregister_task_definition(
            region=self.region,
            test_target_type=self.test_target_type,
            targets=self.test_target_task_definition_arns,
        )

        mock_boto3_client.return_value.deregister_task_definition.assert_has_calls(
            [
                call(taskDefinition="test_task_definition_arn_1"),
            ]
        )

        self.mock_logger.error.assert_called_with(
            pformat(
                "disable_tasks_by_deregister_task_definition - Unknown Error Occurred: Test Exception"
            )
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    @patch("activities.ecs.actions.disable_tasks_by_deregister_task_definition")
    def test_disable_tasks_by_delete_task_definition_success(
        self,
        mock_disable_tasks_by_deregister_task_definition,
        mock_handle_test_target_type,
        mock_boto3_client,
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_disable_tasks_by_deregister_task_definition.side_effect = (
            self.side_effect_disable_tasks_by_deregister_task_definition_success
        )

        mock_boto3_client.return_value.delete_task_definitions.return_value = {}
        disable_tasks_by_delete_task_definition(
            region=self.region,
            test_target_type=self.test_target_type,
            targets=self.test_target_task_definition_arns,
        )

        mock_disable_tasks_by_deregister_task_definition.assert_called_once_with(
            region=self.region,
            test_target_type=self.test_target_type,
            targets=self.test_target_task_definition_arns,
            state_file_name="disable_task_definitions_by_delete.json",
        )

        mock_boto3_client.return_value.delete_task_definitions.assert_has_calls(
            [call(taskDefinitions=self.test_target_task_definition_arns)]
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    @patch("activities.ecs.actions.disable_tasks_by_deregister_task_definition")
    def test_disable_tasks_by_delete_task_definition_failure(
        self,
        mock_disable_tasks_by_deregister_task_definition,
        mock_handle_test_target_type,
        mock_boto3_client,
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        def side_effect_disable_tasks_by_deregister_task_definition_success(
            *args, **kwargs
        ):
            return {target: True for target in kwargs.get("targets")}

        mock_disable_tasks_by_deregister_task_definition.side_effect = (
            side_effect_disable_tasks_by_deregister_task_definition_success
        )

        mock_boto3_client.return_value.delete_task_definitions.return_value = {
            "failures": [
                {"arn": "test_task_definition_arn_1", "reason": "test_failure"}
            ]
        }
        disable_tasks_by_delete_task_definition(
            region=self.region,
            test_target_type=self.test_target_type,
            targets=self.test_target_task_definition_arns,
        )

        mock_disable_tasks_by_deregister_task_definition.assert_called_once_with(
            region=self.region,
            test_target_type="ALL",
            targets=self.test_target_task_definition_arns,
            state_file_name="disable_task_definitions_by_delete.json",
        )

        mock_boto3_client.return_value.delete_task_definitions.assert_has_calls(
            [call(taskDefinitions=self.test_target_task_definition_arns)]
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    @patch("activities.ecs.actions.disable_tasks_by_deregister_task_definition")
    def test_disable_tasks_by_delete_task_definition_deregister_failure(
        self,
        mock_disable_tasks_by_deregister_task_definition,
        mock_handle_test_target_type,
        mock_boto3_client,
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_disable_tasks_by_deregister_task_definition.side_effect = (
            self.side_effect_disable_tasks_by_deregister_task_definition_failure
        )

        print(mock_disable_tasks_by_deregister_task_definition.side_effect)

        disable_tasks_by_delete_task_definition(
            region=self.region,
            test_target_type=self.test_target_type,
            targets=self.test_target_task_definition_arns,
        )

        mock_disable_tasks_by_deregister_task_definition.assert_called_once_with(
            region=self.region,
            test_target_type="ALL",
            targets=self.test_target_task_definition_arns,
            state_file_name="disable_task_definitions_by_delete.json",
        )

    @patch("activities.ecs.actions.disable_tasks_by_deregister_task_definition")
    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_disable_tasks_by_delete_task_definition_exceptions(
        self,
        mock_handle_test_target_type,
        mock_boto3_client,
        mock_disable_tasks_by_deregister_task_definition,
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_disable_tasks_by_deregister_task_definition.side_effect = (
            self.side_effect_disable_tasks_by_deregister_task_definition_success
        )

        mock_boto3_client.return_value.delete_task_definitions.side_effect = (
            ClientError({"Error": {"Code": "400", "Message": "Bad Request"}}, "Test")
        )
        disable_tasks_by_delete_task_definition(
            region=self.region,
            test_target_type=self.test_target_type,
            targets=self.test_target_task_definition_arns,
        )

        mock_disable_tasks_by_deregister_task_definition.assert_called_once_with(
            region=self.region,
            test_target_type=self.test_target_type,
            targets=self.test_target_task_definition_arns,
            state_file_name="disable_task_definitions_by_delete.json",
        )

        self.mock_logger.error.assert_called_with(
            pformat(
                "disable_tasks_by_delete_task_definition - An error occurred (400) when calling the Test operation: Bad Request"
            )
        )

        mock_boto3_client.return_value.delete_task_definitions.side_effect = Exception(
            "Test Exception"
        )

        disable_tasks_by_delete_task_definition(
            region=self.region,
            test_target_type=self.test_target_type,
            targets=self.test_target_task_definition_arns,
        )

        self.mock_logger.error.asssert_called_with(
            pformat(
                f"disable_tasks_by_delete_task_definition - (Exception) An unexpected error occurred: Test Exception"
            )
        )

    @patch("activities.ecs.actions.boto3.client")
    def test_rollback_disable_tasks_by_task_definition(self, mock_boto3_client):

        mock_body = Mock()
        mock_boto3_client.return_value.get_object.return_value = {"Body": mock_body}
        mock_body.read.return_value.decode.return_value = json.dumps(
            {"task_definition_arn": {"deregisteredAt": "huh"}}
        )

        rollback_disable_tasks_by_task_definition(
            region=self.region, state_file_name="test_state_file_name.json"
        )

        mock_boto3_client.return_value.get_object.assert_called_once_with(
            Bucket=S3_BUCKET_NAME, Key="test_state_file_name.json"
        )

        mock_boto3_client.return_value.register_task_definition.assert_called_once_with()

    @patch("activities.ecs.actions.json.loads")
    @patch("activities.ecs.actions.boto3.client")
    def test_rollback_disable_tasks_by_task_definition_empty_state_file(
        self, mock_boto3_client, mock_json_loads
    ):
        mock_boto3_client.return_value.get_object.return_value = {"Body": Mock()}

        mock_json_loads.return_value = None
        rollback_disable_tasks_by_task_definition(region=self.region)

        self.mock_logger.error.assert_called_with(
            pformat(
                "rollback_disable_tasks_by_task_definition - Rollback config empty. Skipping Rollback."
            )
        )

    @patch("activities.ecs.actions.boto3.client")
    def test_rollback_disable_tasks_by_task_definition_exception(
        self, mock_boto3_client
    ):
        mock_s3_client = Mock()
        mock_ecs_client = Mock()
        mock_boto3_client.side_effect = [mock_ecs_client, mock_s3_client]

        mock_s3_client.get_object.side_effect = Exception("Test exception")

        rollback_disable_tasks_by_task_definition(region=self.region)

        self.mock_logger.error.assert_called_with(
            pformat("rollback_disable_tasks_by_task_definition - Test exception")
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_disable_tasks_by_network_inbound(
        self, mock_handle_test_target_type, mock_boto3_client
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": self.test_target_task_arns[0],
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-abc123"}
                            ],
                        }
                    ],
                },
                {
                    "taskArn": self.test_target_task_arns[0],
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-abc123"}
                            ],
                        }
                    ],
                },
            ]
        }
        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [
                {
                    "NetworkInterfaceId": "eni-abc123",
                    "Groups": [{"GroupId": "sg-abc123", "GroupName": "default"}],
                },
                {
                    "NetworkInterfaceId": "eni-def456",
                    "Groups": [{"GroupId": "sg-def456", "GroupName": "custom"}],
                },
            ]
        }
        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {
                    "GroupId": "sg-abc123",
                    "IpPermissions": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 22,
                            "ToPort": 22,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                },
                {
                    "GroupId": "sg-def456",
                    "IpPermissions": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 80,
                            "ToPort": 80,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                },
            ]
        }

        disable_tasks_by_network_inbound(
            region=self.region,
            cluster=self.cluster,
            test_target_type="ALL",
            targets=self.test_target_task_arns,
        )

        mock_ecs_client.describe_tasks.assert_called_with(
            cluster=self.cluster, tasks=self.test_target_task_arns
        )
        mock_ec2_client.describe_network_interfaces.assert_called_with(
            NetworkInterfaceIds=["eni-abc123"]
        )
        mock_ec2_client.describe_security_groups.assert_called_with(
            GroupIds=["sg-abc123", "sg-def456"]
        )

        mock_s3_client.put_object.assert_called_with(
            Bucket=S3_BUCKET_NAME,
            Key="disable_tasks_by_network_inbound.json",
            Body=json.dumps(
                {
                    "sg-abc123": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 22,
                            "ToPort": 22,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                    "sg-def456": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 80,
                            "ToPort": 80,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                }
            ),
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_disable_tasks_by_network_inbound_empty_ingress(
        self, mock_handle_test_target_type, mock_boto3_client
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": self.test_target_task_arns[0],
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-abc123"}
                            ],
                        }
                    ],
                },
                {
                    "taskArn": self.test_target_task_arns[0],
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-abc123"}
                            ],
                        }
                    ],
                },
            ]
        }
        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [
                {
                    "NetworkInterfaceId": "eni-abc123",
                    "Groups": [{"GroupId": "sg-abc123", "GroupName": "default"}],
                },
                {
                    "NetworkInterfaceId": "eni-def456",
                    "Groups": [{"GroupId": "sg-def456", "GroupName": "custom"}],
                },
            ]
        }
        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {
                    "GroupId": "sg-abc123",
                    "IpPermissions": [],
                },
                {
                    "GroupId": "sg-def456",
                    "IpPermissions": [],
                },
            ]
        }

        disable_tasks_by_network_inbound(
            region=self.region,
            cluster=self.cluster,
            test_target_type="ALL",
            targets=self.test_target_task_arns,
        )

        mock_ecs_client.describe_tasks.assert_called_with(
            cluster=self.cluster, tasks=self.test_target_task_arns
        )
        mock_ec2_client.describe_network_interfaces.assert_called_with(
            NetworkInterfaceIds=["eni-abc123"]
        )
        mock_ec2_client.describe_security_groups.assert_called_with(
            GroupIds=["sg-abc123", "sg-def456"]
        )

        mock_s3_client.put_object.assert_called_with(
            Bucket=S3_BUCKET_NAME,
            Key="disable_tasks_by_network_inbound.json",
            Body=json.dumps({"sg-abc123": [], "sg-def456": []}),
        )

        self.mock_logger.info.assert_has_calls(
            [
                call(
                    pformat(
                        "disable_tasks_by_network_inbound - No inbound rules to revoke for security group sg-def456."
                    )
                ),
                call(
                    pformat(
                        "disable_tasks_by_network_inbound - No inbound rules to revoke for security group sg-abc123."
                    )
                ),
            ],
            any_order=True,
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_disable_tasks_by_network_outbound(
        self, mock_handle_test_target_type, mock_boto3_client
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": self.test_target_task_arns[0],
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-abc123"}
                            ],
                        }
                    ],
                },
                {
                    "taskArn": self.test_target_task_arns[0],
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-abc123"}
                            ],
                        }
                    ],
                },
            ]
        }
        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [
                {
                    "NetworkInterfaceId": "eni-abc123",
                    "Groups": [{"GroupId": "sg-abc123", "GroupName": "default"}],
                },
                {
                    "NetworkInterfaceId": "eni-def456",
                    "Groups": [{"GroupId": "sg-def456", "GroupName": "custom"}],
                },
            ]
        }
        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {
                    "GroupId": "sg-abc123",
                    "IpPermissionsEgress": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 22,
                            "ToPort": 22,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                },
                {
                    "GroupId": "sg-def456",
                    "IpPermissionsEgress": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 80,
                            "ToPort": 80,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                },
            ]
        }

        disable_tasks_by_network_outbound(
            region=self.region,
            cluster=self.cluster,
            test_target_type="ALL",
            targets=self.test_target_task_arns,
        )

        mock_ecs_client.describe_tasks.assert_called_with(
            cluster=self.cluster, tasks=self.test_target_task_arns
        )
        mock_ec2_client.describe_network_interfaces.assert_called_with(
            NetworkInterfaceIds=["eni-abc123"]
        )
        mock_ec2_client.describe_security_groups.assert_called_with(
            GroupIds=["sg-abc123", "sg-def456"]
        )

        mock_s3_client.put_object.assert_called_with(
            Bucket=S3_BUCKET_NAME,
            Key="disable_tasks_by_network_outbound.json",
            Body=json.dumps(
                {
                    "sg-abc123": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 22,
                            "ToPort": 22,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                    "sg-def456": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 80,
                            "ToPort": 80,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                }
            ),
        )

        mock_ec2_client.revoke_security_group_egress.assert_has_calls(
            [
                call(
                    GroupId="sg-abc123",
                    IpPermissions=[
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 22,
                            "ToPort": 22,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                )
            ]
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_disable_tasks_by_network_outbound_empty_egress(
        self, mock_handle_test_target_type, mock_boto3_client
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_ecs_client = Mock()
        mock_ec2_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_ec2_client,
            mock_s3_client,
        ]

        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": self.test_target_task_arns[0],
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-abc123"}
                            ],
                        }
                    ],
                },
                {
                    "taskArn": self.test_target_task_arns[0],
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-abc123"}
                            ],
                        }
                    ],
                },
            ]
        }
        mock_ec2_client.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [
                {
                    "NetworkInterfaceId": "eni-abc123",
                    "Groups": [{"GroupId": "sg-abc123", "GroupName": "default"}],
                },
                {
                    "NetworkInterfaceId": "eni-def456",
                    "Groups": [{"GroupId": "sg-def456", "GroupName": "custom"}],
                },
            ]
        }
        mock_ec2_client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {
                    "GroupId": "sg-abc123",
                    "IpPermissionsEgress": [],
                },
                {
                    "GroupId": "sg-def456",
                    "IpPermissionsEgress": [],
                },
            ]
        }

        disable_tasks_by_network_outbound(
            region=self.region,
            cluster=self.cluster,
            test_target_type="ALL",
            targets=self.test_target_task_arns,
        )

        mock_ecs_client.describe_tasks.assert_called_with(
            cluster=self.cluster, tasks=self.test_target_task_arns
        )
        mock_ec2_client.describe_network_interfaces.assert_called_with(
            NetworkInterfaceIds=["eni-abc123"]
        )
        mock_ec2_client.describe_security_groups.assert_called_with(
            GroupIds=["sg-abc123", "sg-def456"]
        )

        mock_s3_client.put_object.assert_called_with(
            Bucket=S3_BUCKET_NAME,
            Key="disable_tasks_by_network_outbound.json",
            Body=json.dumps(
                {
                    "sg-abc123": [],
                    "sg-def456": [],
                }
            ),
        )

        self.mock_logger.info.assert_has_calls(
            [
                call(
                    pformat(
                        "disable_tasks_by_network_outbound - No outbound rules to revoke for security group sg-def456."
                    )
                ),
                call(
                    pformat(
                        "disable_tasks_by_network_outbound - No outbound rules to revoke for security group sg-abc123."
                    )
                ),
            ],
            any_order=True,
        )

    @patch("activities.ecs.actions.boto3.client")
    def test_rollback_disable_tasks_by_network_inbound(self, mock_boto3_client):

        mock_boto3_client.return_value.get_object.return_value = {
            "Body": Mock(
                read=Mock(
                    return_value='{"security_group_id": "ingress_rules"}'.encode("utf8")
                )
            )
        }
        mock_boto3_client.return_value.authorize_security_group_ingress.return_value = (
            {}
        )

        rollback_disable_tasks_by_network_inbound(region=self.region)

        mock_boto3_client.return_value.get_object.assert_called_with(
            Bucket=S3_BUCKET_NAME, Key="disable_task_by_network_inbound.json"
        )
        mock_boto3_client.return_value.authorize_security_group_ingress.assert_called_with(
            GroupId="security_group_id", IpPermissions="ingress_rules"
        )

    @patch("activities.ecs.actions.json.loads")
    @patch("activities.ecs.actions.boto3.client")
    def test_rollback_disable_tasks_by_network_inbound_empty_state_file(
        self, mock_boto3_client, mock_json_loads
    ):

        mock_boto3_client.return_value.get_object.return_value = {"Body": Mock()}

        mock_json_loads.return_value = None
        rollback_disable_tasks_by_network_inbound(region=self.region)

        self.mock_logger.error.assert_called_with(
            pformat(
                "rollback_disable_tasks_by_network_inbound - Rollback config empty. Skipping Rollback."
            )
        )

    @patch("activities.ecs.actions.boto3.client")
    def test_rollback_disable_tasks_by_network_inbound_exception(
        self, mock_boto3_client
    ):

        mock_boto3_client.return_value.get_object.side_effect = Exception(
            "Unexpected error"
        )

        rollback_disable_tasks_by_network_inbound(region=self.region)

        self.mock_logger.error.assert_called_with(
            pformat("rollback_disable_tasks_by_network_inbound - Unexpected error")
        )

    @patch("activities.ecs.actions.boto3.client")
    def test_rollback_disable_tasks_by_network_outbound(self, mock_boto3_client):

        mock_boto3_client.return_value.get_object.return_value = {
            "Body": Mock(
                read=Mock(
                    return_value='{"security_group_id": "egress_rules"}'.encode("utf8")
                )
            )
        }
        mock_boto3_client.return_value.authorize_security_group_egress.return_value = {}

        rollback_disable_tasks_by_network_outbound(region=self.region)

        mock_boto3_client.return_value.get_object.assert_called_with(
            Bucket=S3_BUCKET_NAME, Key="disable_task_by_network_outbound.json"
        )
        mock_boto3_client.return_value.authorize_security_group_egress.assert_called_with(
            GroupId="security_group_id", IpPermissions="egress_rules"
        )

    @patch("activities.ecs.actions.json.loads")
    @patch("activities.ecs.actions.boto3.client")
    def test_rollback_disable_tasks_by_network_outbound_empty_state_file(
        self, mock_boto3_client, mock_json_loads
    ):

        mock_boto3_client.return_value.get_object.return_value = {"Body": Mock()}

        mock_json_loads.return_value = None
        rollback_disable_tasks_by_network_outbound(region=self.region)

        self.mock_logger.error.assert_called_with(
            pformat(
                "rollback_disable_tasks_by_network_outbound - Rollback config empty. Skipping Rollback."
            )
        )

    @patch("activities.ecs.actions.boto3.client")
    def test_rollback_disable_tasks_by_network_outbound_exception(
        self, mock_boto3_client
    ):

        mock_boto3_client.return_value.get_object.side_effect = Exception(
            "Unexpected error"
        )

        rollback_disable_tasks_by_network_outbound(region=self.region)

        self.mock_logger.error.assert_called_with(
            pformat("rollback_disable_tasks_by_network_outbound - Unexpected error")
        )


class TestDisableTaskDefinitions(unittest.TestCase):
    def setUp(self):
        self.region = "test_region"
        self.cluster = "test_cluster"
        self.test_target_type = "ALL"

        self.test_target_task_arns = ["test_task_arn_1", "test_task_arn_2"]
        self.test_target_task_definition_arns = [
            "test_task_definition_arn_1",
            "test_task_definition_arn_2",
        ]

        self.mock_logger = patch.object(activities.ecs.actions, "logger").start()

    def tearDown(self):
        patch.stopall()

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_disable_task_definitions_by_invalid_iam(
        self, mock_handle_test_target_type, mock_boto3_client
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_ecs_client = Mock()
        mock_iam_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [
            mock_ecs_client,
            mock_iam_client,
            mock_s3_client,
        ]

        targets = ["target1", "target2"]

        ecs_response = {
            "taskDefinition": {"taskRoleArn": "arn:aws:iam::123456789012:role/test"}
        }
        iam_response = {
            "PolicyNames": ["policy1", "policy2"],
            "AttachedPolicies": [
                {
                    "PolicyName": "testName",
                    "PolicyArn": "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
                }
            ],
        }
        s3_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        mock_ecs_client.describe_task_definition.return_value = ecs_response
        mock_iam_client.list_role_policies.return_value = iam_response
        mock_iam_client.get_role_policy.return_value = {
            "PolicyName": "policy1",
            "PolicyDocument": "doc1",
        }
        mock_iam_client.list_attached_role_policies.return_value = iam_response
        mock_s3_client.put_object.return_value = s3_response

        disable_task_definitions_by_invalid_iam(
            region=self.region,
            test_target_type=self.test_target_type,
            targets=self.test_target_task_definition_arns,
        )

        mock_ecs_client.describe_task_definition.assert_has_calls(
            [
                call(taskDefinition=self.test_target_task_definition_arns[0]),
                call(taskDefinition=self.test_target_task_definition_arns[1]),
            ]
        )

        mock_iam_client.list_role_policies.assert_has_calls(
            [
                call(RoleName="test"),
                call(RoleName="test"),
            ]
        )

        mock_iam_client.get_role_policy.assert_has_calls(
            [
                call(RoleName="test", PolicyName="policy1"),
                call(RoleName="test", PolicyName="policy2"),
            ]
        )

        mock_iam_client.list_attached_role_policies.assert_has_calls(
            [
                call(RoleName="test"),
                call(RoleName="test"),
            ]
        )

        mock_s3_client.put_object.assert_has_calls(
            [
                call(
                    Bucket=S3_BUCKET_NAME,
                    Key="disable_task_definitions_by_invalid_iam.json",
                    Body=json.dumps(
                        {
                            "test": {
                                "inline_policies": [
                                    {"policy1": "doc1"},
                                    {"policy1": "doc1"},
                                ],
                                "managed_policies": [
                                    {
                                        "PolicyName": "testName",
                                        "PolicyArn": "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
                                    }
                                ],
                            }
                        }
                    ),
                )
            ]
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_rollback_disable_task_definitions_by_invalid_iam(
        self, mock_handle_test_target_type, mock_boto3_client
    ):

        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_iam_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [mock_iam_client, mock_s3_client]

        s3_response = {
            "Body": Mock(
                read=Mock(
                    return_value='{"arn:aws:iam::123456789012:role/test": {"inline_policies": [{"policy1": "document1"}], "managed_policies": [{"PolicyArn": "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"}]}}'.encode(
                        "utf8"
                    )
                )
            )
        }
        iam_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        mock_s3_client.get_object.return_value = s3_response
        mock_iam_client.put_role_policy.return_value = iam_response
        mock_iam_client.attach_role_policy.return_value = iam_response

        rollback_disable_task_definitions_by_invalid_iam(region=self.region)

        mock_s3_client.get_object.assert_called_with(
            Bucket=S3_BUCKET_NAME, Key="disable_task_definitions_by_invalid_iam.json"
        )
        mock_iam_client.put_role_policy.assert_called_with(
            RoleName="arn:aws:iam::123456789012:role/test",
            PolicyName="policy1",
            PolicyDocument=json.dumps("document1"),
        )
        mock_iam_client.attach_role_policy.assert_called_with(
            RoleName="arn:aws:iam::123456789012:role/test",
            PolicyArn="arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
        )

    @patch("activities.ecs.actions.boto3.client")
    @patch("activities.ecs.actions.handle_test_target_type")
    def test_rollback_disable_task_definitions_by_invalid_iam_exception(
        self, mock_handle_test_target_type, mock_boto3_client
    ):
        def side_effect_handle_test_target_type(*args, **kwargs):
            return kwargs.get("targets")

        mock_handle_test_target_type.side_effect = side_effect_handle_test_target_type

        mock_iam_client = Mock()
        mock_s3_client = Mock()

        mock_boto3_client.side_effect = [mock_iam_client, mock_s3_client]

        mock_s3_client.get_object.side_effect = Exception("Test exception")

        rollback_disable_task_definitions_by_invalid_iam(region=self.region)

        self.mock_logger.error.assert_called_with(
            pformat("rollback_disable_task_definitions_by_invalid_iam - Test exception")
        )

    @patch("activities.ecs.actions.json.loads")
    @patch("activities.ecs.actions.boto3.client")
    def test_rollback_disable_task_definitions_by_invalid_iam_empty_state_file(
        self, mock_boto3_client, mock_json_loads
    ):

        mock_boto3_client.return_value.get_object.return_value = {"Body": Mock()}

        mock_json_loads.return_value = None
        rollback_disable_task_definitions_by_invalid_iam(region=self.region)

        self.mock_logger.error.assert_called_with(
            pformat(
                "rollback_disable_task_definitions_by_invalid_iam - Rollback config empty. Skipping Rollback."
            )
        )


if __name__ == "__main__":
    unittest.main()
