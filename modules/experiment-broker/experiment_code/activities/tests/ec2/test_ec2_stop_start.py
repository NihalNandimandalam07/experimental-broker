import unittest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError, WaiterError
from chaoslib.exceptions import ActivityFailed

import activities.ec2.actions
import activities.ec2.probes
from activities.ec2.actions import stop_ec2_instance, start_ec2_instance
from activities.ec2.probes import check_ec2_instance_running


def state_change(response_key, previous, current, instance_id="i-123"):
    return {
        response_key: [
            {
                "InstanceId": instance_id,
                "PreviousState": {"Name": previous},
                "CurrentState": {"Name": current},
            }
        ]
    }


class TestStopStartActions(unittest.TestCase):
    instance_id = "i-123"
    region = "us-east-2"
    client_error = ClientError(
        {"Error": {"Code": "InvalidInstanceID.NotFound", "Message": "not found"}},
        "StopInstances",
    )

    def setUp(self):
        patch.object(activities.ec2.actions, "logger").start()
        self.mock_boto3 = patch.object(activities.ec2.actions, "boto3").start()
        self.client = self.mock_boto3.client.return_value

    def tearDown(self):
        patch.stopall()

    def test_stop_waits_and_returns_state(self):
        self.client.stop_instances.return_value = state_change(
            "StoppingInstances", "running", "stopping"
        )

        result = stop_ec2_instance(self.instance_id, self.region, timeout=60)

        self.mock_boto3.client.assert_called_once_with("ec2", region_name=self.region)
        self.client.stop_instances.assert_called_once_with(InstanceIds=[self.instance_id])
        self.client.get_waiter.assert_called_once_with("instance_stopped")
        self.client.get_waiter.return_value.wait.assert_called_once_with(
            InstanceIds=[self.instance_id],
            WaiterConfig={"Delay": 15, "MaxAttempts": 4},
        )
        self.assertEqual(
            result,
            {
                "instance_id": self.instance_id,
                "previous_state": "running",
                "current_state": "stopping",
            },
        )

    def test_start_waits_for_running(self):
        self.client.start_instances.return_value = state_change(
            "StartingInstances", "stopped", "pending"
        )

        result = start_ec2_instance(self.instance_id, self.region)

        self.client.start_instances.assert_called_once_with(InstanceIds=[self.instance_id])
        self.client.get_waiter.assert_called_once_with("instance_running")
        self.assertEqual(result["current_state"], "pending")

    def test_no_wait_skips_waiter(self):
        self.client.stop_instances.return_value = state_change(
            "StoppingInstances", "running", "stopping"
        )

        stop_ec2_instance(self.instance_id, self.region, wait=False)

        self.client.get_waiter.assert_not_called()

    def test_client_error_raises_activity_failed(self):
        self.client.stop_instances.side_effect = self.client_error

        with self.assertRaises(ActivityFailed):
            stop_ec2_instance(self.instance_id, self.region)

    def test_waiter_timeout_raises_activity_failed(self):
        self.client.start_instances.return_value = state_change(
            "StartingInstances", "stopped", "pending"
        )
        self.client.get_waiter.return_value.wait.side_effect = WaiterError(
            "InstanceRunning", "Max attempts exceeded", {}
        )

        with self.assertRaises(ActivityFailed):
            start_ec2_instance(self.instance_id, self.region)


class TestCheckEc2InstanceRunning(unittest.TestCase):
    instance_id = "i-123"

    def setUp(self):
        patch.object(activities.ec2.probes, "logger").start()
        self.mock_boto3 = patch.object(activities.ec2.probes, "boto3").start()
        self.client = self.mock_boto3.client.return_value

    def tearDown(self):
        patch.stopall()

    def describe(self, state):
        return {"Reservations": [{"Instances": [{"State": {"Name": state}}]}]}

    def test_running(self):
        self.client.describe_instances.return_value = self.describe("running")
        self.assertTrue(check_ec2_instance_running(self.instance_id))

    def test_stopped(self):
        self.client.describe_instances.return_value = self.describe("stopped")
        self.assertFalse(check_ec2_instance_running(self.instance_id))

    def test_not_found(self):
        self.client.describe_instances.return_value = {"Reservations": []}
        self.assertFalse(check_ec2_instance_running(self.instance_id))

    def test_client_error(self):
        self.client.describe_instances.side_effect = ClientError(
            {"Error": {"Code": "InvalidInstanceID.NotFound", "Message": "x"}},
            "DescribeInstances",
        )
        self.assertFalse(check_ec2_instance_running(self.instance_id))


if __name__ == "__main__":
    unittest.main()
