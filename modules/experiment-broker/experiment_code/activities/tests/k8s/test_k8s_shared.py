import unittest
from unittest.mock import Mock, patch

from activities.k8s.shared import install_stress_ng_on_pod


class TestKubernetesActions(unittest.TestCase):
    @patch("activities.k8s.shared.boto3")
    def test_install_stress_ng_on_pod(self, mock_boto3):
        install_stress_ng_on_pod("Name", ["node1", "node2"])

        mock_boto3.Session().client().send_command.assert_called_with(
            Targets=[{"Key": "Name", "Values": ["node1", "node2"]}],
            DocumentName="InstallStressNG",
        )
