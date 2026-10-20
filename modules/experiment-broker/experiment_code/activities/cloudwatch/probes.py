import random
import logging
from typing import Literal
from time import sleep
from helpers.shared import get_logger
from chaosaws import aws_client, Configuration

logger: logging.Logger = get_logger(__name__, activity=True)


def probe_alarm_state(
    alarm_name,
    alarm_state: Literal["OK", "ALARM", "INSUFFICIENT_DATA"],
    timeout: int = 60,
    configuration: Configuration = None,
) -> bool:
    """
    Finds the state of a metric alarm in CloudWatch.

    Args:
        alarm_name (str): The name of the alarm to probe.
        alarm_state (str): The expected state of the alarm.
        timeout (int): The maximum time to wait for the alarm to reach the expected state.
        configuration (Configuration): The AWS configuration details.

    Returns:
        bool: True if the alarm state matches the expected state, False otherwise.
    """
    try:
        if alarm_state not in ["OK", "ALARM", "INSUFFICIENT_DATA"]:
            logger.error(f"Invalid alarm state: {alarm_state}")
            raise ValueError(
                "Invalid alarm state. Must be one of 'OK', 'ALARM', 'INSUFFICIENT_DATA'"
            )

        logger.info(f"Probing Alarm {alarm_name}")

        cloudwatch_client = aws_client("cloudwatch", configuration=configuration)
        time_elapsed = 0
        match = False
        while (match == False) and (time_elapsed < timeout):
            alarms = cloudwatch_client.describe_alarms(AlarmNames=[alarm_name])[
                "MetricAlarms"
            ]
            if len(alarms) == 0:
                logger.error(f"Alarm {alarm_name} not found")
                raise ValueError(f"Alarm {alarm_name} not found.")

            discovered_alarm_state = alarms[0]["StateValue"]
            match = discovered_alarm_state == alarm_state
            logger.info(
                f"Alarm State is {discovered_alarm_state}, Expected: {alarm_state}, Match: {match}"
            )
            if match == False:
                logger.info("Alarm not in expected state. Waiting for 10 seconds...")
                time_elapsed += 10
                sleep(10)

        return {"match": match, "alarm_state": discovered_alarm_state}
    except Exception as e:
        logger.error(f"Error probing alarm state: {str(e)}")
        raise e
