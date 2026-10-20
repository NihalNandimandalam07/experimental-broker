from typing import Any

from chaoslib.exceptions import FailedActivity
from chaoslib.types import Configuration, Secrets
from experiment_broker_logging.logging import logger
from activities.helpers.shared import handle_pagination

from chaosaws import aws_client
from chaosaws.types import AWSResponse

def get_experiment_by_tag(tag_key: str, tag_value: str, fis_client: Any = None, configuration: Configuration = None) -> AWSResponse:
    """
    Return the newest experiment for the provided tag key and tag value
    """

    raise NotImplementedError

def get_latest_experiment(experiment_template_id: str, fix_client: Any = None, configuration: Configuration = None) -> AWSResponse:
    """
    Returns the newest experiment for the provided experiment template id.
    """

    if not configuration:
        raise FailedActivity("A configuration must be provided.")
    
    if not fis_client:
        fis_client = aws_client("fis", configuration=configuration)

    try:
        experiments = handle_pagination(fis_client, list_experiments", experimentTemplateId=experiment_template_id)
        return max(experiments,key=lambda x: x["creationTime"])
    except Exception as e:
        raise FailedActivity(e)
