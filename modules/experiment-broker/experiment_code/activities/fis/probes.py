from typing import Dict, Any, Literal

from chaoslib.exceptions import FailedActivity
from chaoslib.types import Configuration, Secrets
from experiment_broker_logging.logging import logger

from chaosaws import aws_client
from chaosaws.types import AWSResponse

from activities.fis.shared import get_latest_experiment
from activities.helpers.shared import handle_pagination

import time

__all__ = ["get_experiment", "assert_experiment_status"]


def get_experiment(
    experiment_id: str, configuration: Configuration = None, secrets: Secrets = None
) -> AWSResponse:
    """
    Gets information about the specified experiment.

    :param experiment_id: str representing the id of the experiment to fetch information
        of
    :param configuration: Configuration object representing the CTK Configuration
    :param secrets: Secret object representing the CTK Secrets
    :returns: AWSResponse representing the response from FIS upon retrieving the
        experiment information

    Examples
    --------
    >>> get_experiment(
    ...    experiment_id="EXPTUCK2dxepXgkR38"
    ... )
    {'ResponseMetadata': {'RequestId': '0665fe39-2213-400b-b7ff-5f1ab9b7a5ea',
    'HTTPStatusCode': 200, 'HTTPHeaders': {'date': 'Fri, 20 Aug 2021 11:08:27 GMT',
    ...
    'experiment': {'id': 'EXPTUCK2dxepXgkR38',
    'experimentTemplateId': 'EXT6oWVA1WrLNy4XS',
    ...
    }
    """

    if not experiment_id:
        raise FailedActivity(
            "You must pass a valid experiment id, id provided was empty"
        )

    fis_client = aws_client(
        resource_name="fis", configuration=configuration, secrets=secrets
    )

    try:
        return fis_client.get_experiment(id=experiment_id)
    except Exception as ex:
        raise FailedActivity(f"Get Experiment failed, reason was: {ex}")
    
def asset_experiment_status(
    expected_status: Literal["pending", "initiating", "running", "completed", "stopping", "stopped", "failed"],
    configuration: Configuration,
    experiment_id: str = None,
    experiment_template_id: str = None,
    timeout: int = 1800,
    retry_after: int = 30,
) -> bool:

    """
    Usage Notes TODO
    """

    if expected_status not in ["pending", "initiating", "running", "completed", "stopping", "stopped", "failed"]:
        raise FailedActivity(f"expected_status should be one of 'pending', 'initiating', 'running', 'completed', 'stopping', 'stopped', 'failed'. Provided status was {expected_status}")

    if experiment_template_id == None and experiment_id == None:
        raise FailedActivity("Either 'experiment_id' or 'experiment_template_id' must be provided.")

    start_time = time.time()
    while True:
        experiment = get_experiment(experiment_id, configuration)["experiment"]
        if experiment["state"]["status"] == expected_status:
            return True
        elif time.time() - start_time > timeout:
            break
        else:
            logger.info(f"Retrying assertion after {retry_after} seconds...")
            time.sleep(retry_after)
    
    raise FailedActivity(f"ASSERTIONERROR: Experiment status is {experiment['state']['status']} with reason {experiment['state']['status']}. Expected state was {expected_status}")

def assert_experiment_action_status(
    action_name: str,
    expected_status: Literal["pending", "initiating", "running", "completed", "stopping", "stopped", "failed"],
    configuration: Configuration,
    experiment_id: str = None,
    experiment_template_id: str = None,
    timeout: int = 1800,
    retry_after: int = 30,
) -> bool:
    """
    Usage Notes TODO
    """

    if expected_status not in ["pending", "initiating", "running", "completed", "stopping", "stopped", "failed"]:
        raise FailedActivity(f"expected_status should be one of 'pending', 'initiating', 'running', 'completed', 'stopping', 'stopped', 'failed'. Provided status was '{expected_status}'")

    if experiment_template_id == None and experiment_id == None:
        raise FailedActivity("Either 'experiment_id' or 'experiment_template_id' must be provided.")
    
    if not experiment_id:
        experiment_id = get_latest_experiment(experiment_template_id=experiment_template_id,configuration=configuration)["id"]

    start_time = time.time()
    while True:
        experiment = get_experiment(experiment_id, configuration)["experiment"]

        if experiment["actions"].get(action_name, None) == None:
            raise FailedActivity(f"action_name: {action_name} is not an action in experiment {experiment_id}.")
        elif experiment["actions"][action_name]["state"]["status"] == expected_status:
            return True
        elif time.time() - start_time > timeout:
            break
        else:
            logger.info(f"Expected Status: {expected_status}. Status Found: {experiment['actions'][action_name]['state']['status']}")
            logger.info(f"Retrying assertion after {retry_after} seconds...")
            time.sleep(retry_after)

    raise FailedActivity(f"ASSERTIONERROR: Experiment status is {experiment['actions'][action_name]['state']['status']} with reason {experiment['experiment']['actions'][action_name]['state']['reason']}. Expected state was {expected_status}")

def assert_no_active_experiments(experiment_template_id: str, configuration: Configuration) -> bool:
    """
    Usage Notes TODO
    """

    fis_client = aws_client("fis, configuration=configuration")
    experiments = handle_pagination(fis_client, 'list_experiments')

    active_experiments = [experiment for experiment in experiments if experiment['state']['status'] not in ["pending", "initiating", "running", "stopping"]]

    if len(active_experiments) == 0:
        return True
    
    err_log = {}
    for experiment in active_experiments:
        err_log[experiment["id"]] = experiment["state"]

    raise FailedActivity(f"ASSERTIONERROR: Active experiments found: {err_log}")