import unittest
from unittest.mock import Mock, patch

from activities.ec2.actions import (
    stress_all_network_io,
    stress_io,
    stress_memory,
    stress_network_latency,
    stress_network_utilization,
    stress_packet_loss,
)


class TestEC2Actions(unittest.TestCase):
    @patch("activities.ec2.actions.boto3")
    def test_packet_loss(self, mock_boto3):
        stress_packet_loss("Name", ["node1"])

        mock_boto3.Session().client().send_command.assert_called_with(
            Targets=[{"Key": "Name", "Values": ["node1"]}],
            DocumentName="StressPacketLoss",
            Parameters={
                "interface": ["ens5"],
                "portNumber": ["0"],
                "portType": ["dport"],
                "loss": ["50"],
                "duration": ["60"],
            },
        )

    @patch("activities.ec2.actions.boto3")
    def test_stress_memory(self, mock_boto3):
        stress_memory("Name", ["node1"])

        mock_boto3.Session().client().send_command.assert_called_with(
            Targets=[{"Key": "Name", "Values": ["node1"]}],
            DocumentName="StressMemory",
            Parameters={"duration": ["60"], "workers": ["4"], "percent": ["99"]},
        )

    @patch("activities.ec2.actions.boto3")
    def test_stress_latency(self, mock_boto3):
        stress_network_latency("Name", ["node1"])

        mock_boto3.Session().client().send_command.assert_called_with(
            Targets=[{"Key": "Name", "Values": ["node1"]}],
            DocumentName="NetworkLatency",
            Parameters={
                "duration": ["60"],
                "ports": ["1"],
                "portType": ["sport"],
                "delay": ["50"],
                "interface": ["ens5"],
            },
        )

    @patch("activities.ec2.actions.boto3")
    def test_stress_io(self, mock_boto3):
        stress_io("Name", ["node1"])

        mock_boto3.Session().client().send_command.assert_called_with(
            Targets=[{"Key": "Name", "Values": ["node1"]}],
            DocumentName="StressIO",
            Parameters={"duration": ["60"], "iomix": ["50"], "percent": ["99"]},
        )

    @patch("activities.ec2.actions.boto3")
    def test_stress_network_util(self, mock_boto3):
        stress_network_utilization("Name", ["node1"])

        mock_boto3.Session().client().send_command.assert_called_with(
            Targets=[{"Key": "Name", "Values": ["node1"]}],
            DocumentName="StressNetworkUtilization",
            Parameters={"duration": ["60"], "workers": ["4"], "percent": ["99"]},
        )

    @patch("activities.ec2.actions.boto3")
    def test_stress_all_network(self, mock_boto3):
        stress_all_network_io("Name", ["node1"])

        mock_boto3.Session().client().send_command.assert_called_with(
            Targets=[{"Key": "Name", "Values": ["node1"]}],
            DocumentName="StressNetworkUtilization",
            Parameters={"duration": ["60"]},
        )
