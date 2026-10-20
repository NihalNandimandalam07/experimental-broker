import unittest
from unittest.mock import Mock, patch, call
from botocore.exceptions import ClientError
import datetime
import logging
import json
from pprint import pformat

import activities.cloudtrail.probes
from activities.cloudtrail.probes import assert_cloudtrail_events_occurred

handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)
logger.addHandler(handler)


class TestProbes(unittest.TestCase):

    def setUp(self):
        self.mock_logger = patch.object(
            activities.cloudtrail.probes, "logger"
        ).start()

    def tearDown(self):
        patch.stopall()

    def side_effect_attempt_retry(*args, **kwargs):
        if kwargs.get("retry") == False:
            raise AssertionError("Not retrying")
        if kwargs.get("current_iteration_time") >= kwargs.get(
            "max_duration_to_iterate"
        ):
            raise AssertionError("Max duration reached")

    @patch("activities.cloudtrail.probes.time.sleep")
    @patch("activities.cloudtrail.probes.boto3.client")
    def test_assert_cloudtrail_events_occurred_value_errors(
        self, mock_boto3_client, mock_time_sleep
    ):
        mock_cloudtrail_client = Mock()
        mock_boto3_client.return_value = mock_cloudtrail_client

        with self.assertRaises(ValueError):
            assert_cloudtrail_events_occurred(
                region="test_region",
                event_names=["test_event"],
                filter_type="InvalidFilterType",
                filter_value="test_value",
            )

        with self.assertRaises(ValueError):
            assert_cloudtrail_events_occurred(
                region="test_region",
                event_names=["test_event"],
                filter_type="EventId",
                start_time=datetime.datetime.now() + datetime.timedelta(days=1),
                end_time=datetime.datetime.now() - datetime.timedelta(days=1),
            )

    @patch("activities.cloudtrail.probes.time.sleep")
    @patch("activities.cloudtrail.probes.boto3.client")
    def test_assert_cloudtrail_events_occurred_no_filter_value(
        self, mock_boto3_client, mock_time_sleep
    ):
        mock_cloudtrail_client = Mock()
        mock_boto3_client.return_value = mock_cloudtrail_client

        mock_cloudtrail_client.lookup_events.return_value = {
            "Events": [{"EventName": "test_event"}]
        }

        resp = assert_cloudtrail_events_occurred(
            region="test_region",
            event_names=["test_event"],
            filter_type="EventName",
            filter_value=None,
        )

        assert self.mock_logger.warning.call_count == 1

    @patch("activities.cloudtrail.probes.time.sleep")
    @patch("activities.cloudtrail.probes.attempt_retry")
    @patch("activities.cloudtrail.probes.boto3.client")
    def test_assert_cloudtrail_events_occurred_failure(
        self, mock_boto3_client, mock_attempt_retry, mock_time_sleep
    ):

        mock_cloudtrail_client = Mock()
        mock_boto3_client.return_value = mock_cloudtrail_client

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_cloudtrail_client.lookup_events.return_value = {"Events": []}

        with self.assertRaises(AssertionError):
            resp = assert_cloudtrail_events_occurred(
                region="test_region",
                event_names=["test_event"],
                filter_type="EventName",
                filter_value=None,
            )

    @patch("activities.cloudtrail.probes.time.sleep")
    @patch("activities.cloudtrail.probes.attempt_retry")
    @patch("activities.cloudtrail.probes.boto3.client")
    def test_assert_cloudtrail_events_occurred_eventual_success(
        self, mock_boto3_client, mock_attempt_retry, mock_time_sleep
    ):
        mock_cloudtrail_client = Mock()
        mock_boto3_client.return_value = mock_cloudtrail_client

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_cloudtrail_client.lookup_events.side_effect = [
            {"Events": []},
            {"Events": [{"EventName": "test_event"}]},
        ]

        resp = assert_cloudtrail_events_occurred(
            region="test_region",
            event_names=["test_event"],
            filter_type="EventName",
            filter_value=None,
            retry=True,
        )

        assert self.mock_logger.warning.call_count == 1

    @patch("activities.cloudtrail.probes.time.sleep")
    @patch("activities.cloudtrail.probes.attempt_retry")
    @patch("activities.cloudtrail.probes.boto3.client")
    def test_assert_cloudtrail_events_occurred_filter_success(
        self, mock_boto3_client, mock_attempt_retry, mock_time_sleep
    ):
        mock_cloudtrail_client = Mock()
        mock_boto3_client.return_value = mock_cloudtrail_client

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_cloudtrail_client.lookup_events.side_effect = [
            {"Events": []},
            {"Events": [{"EventName": "test_event", "Username": "test_resource"}]},
        ]

        resp = assert_cloudtrail_events_occurred(
            region="test_region",
            event_names=["test_event"],
            filter_type="Username",
            filter_value="test_resource",
            retry=True,
        )

        assert self.mock_logger.info.call_count == 1

    @patch("activities.cloudtrail.probes.time.sleep")
    @patch("activities.cloudtrail.probes.attempt_retry")
    @patch("activities.cloudtrail.probes.boto3.client")
    def test_assert_cloudtrail_events_occurred_start_time_end_time(
        self, mock_boto3_client, mock_attempt_retry, mock_time_sleep
    ):
        mock_cloudtrail_client = Mock()
        mock_boto3_client.return_value = mock_cloudtrail_client

        mock_attempt_retry.side_effect = self.side_effect_attempt_retry

        mock_cloudtrail_client.lookup_events.side_effect = [
            {"Events": [{"EventName": "test_event"}]},
        ]

        start_time = datetime.datetime.now() - datetime.timedelta(days=1)
        end_time = datetime.datetime.now()

        resp = assert_cloudtrail_events_occurred(
            region="test_region",
            event_names=["test_event"],
            start_time=start_time,
            end_time=end_time,
        )

        assert self.mock_logger.info.call_count == 1


if __name__ == "__main__":
    unittest.main()
