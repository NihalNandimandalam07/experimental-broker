import io
import logging
import sys
import os
import json
import boto3
import traceback

from datetime import datetime
from activities.opensearch.shared import upload_experiment_journal
from activities.s3.shared import get_object, create_presigned_url, put_object
from chaoslib.experiment import run_experiment
from chaoslib.loader import load_experiment
from logzero import logger

# name the package: resiliency (chaostoolkit-resiliency)


def handler(event, context):
    """Runs an experiment by `experiment_source`.

    Provide the following event data to invoke the function:

    {
      "experiment_source": "authorizations/tc001.yml",
      "bucket_name": "chaos-testing-bucket",
      ...(additional values for running experiment: AZ, Region, Environment, etc.)
    }
    """
    log_capture, report_capture = __capture_experiment_logs()

    experiment_source = event.get("experiment_source")
    experiment_state = event.get("state")
    output_config = event.get("output_config")
    if experiment_source:
        logger.info("ChaosToolkit attempting to load experiment: %s", experiment_source)

    try:
        get_object(
            bucket_name=event.get("bucket_name"),
            filename=experiment_source,
            configuration=event.get("configuration", {}),
        )
    except Exception as e:
        logger.exception("Unable to retrieve experiment %s: %s", experiment_source, e)
        raise
    url = create_presigned_url(event.get("bucket_name"), experiment_source)
    experiment = load_experiment(url)

    # experiment_journal = run_experiment(experiment, strategy=Strategy.DURING_METHOD, schedule=Schedule(continuous_hypothesis_frequency=15, fail_fast=True))
    experiment_journal = run_experiment(experiment)
    # experiment_journal["jira_exec_ticket"] = event["jira_exec_ticket"]
    # experiment_journal["jira_test_ticket"] = event["jira_test_ticket"]

    print("Journal contents: " + str(experiment_journal))
    if (
        experiment_journal.get("status") == "success"
        or experiment_journal.get("status") == "completed"
    ):
        event.update({"state": "done"})
    else:
        event.update({"state": "failed"})

    try:
        key = f"{event['output_path']}{experiment_source.split('/')[-1].split('.')[0]}/{datetime.now().strftime('%Y-%M-%d-%H-%M')}"
        logger.info(f"uploading object {key}")
        output_s3 = put_object(
            bucket_name=event["output_bucket"],
            key=key,
            contents=json.dumps(experiment_journal),
        )
        logger.info(
            f"Experiment journal uploaded to S3 as: s3://{event['output_bucket']}/{key}"
        )
    except Exception:
        exc_str = traceback.format_exc()
        logger.error(f"Unable to upload experiment journal to S3: {exc_str}")

    event.update({"response": json.dumps(experiment_journal)})
    event.update({"report_capture": str(report_capture.getvalue())})

    return event


def __capture_experiment_logs():
    """Captures logs for ChaosToolkit experiments"""
    log_capture_string = io.StringIO()
    error_handler = logging.StreamHandler(log_capture_string)
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)

    report_capture_string = io.StringIO()
    info_handler = logging.StreamHandler(report_capture_string)
    info_handler.setLevel(logging.INFO)
    logger.addHandler(info_handler)

    return log_capture_string, report_capture_string


if __name__ == "__main__":
    variables = [
        "bucket_name",
        "experiment_source",
        "output_bucket",
        "output_path",
        "jira_exec_ticket",
        "jira_test_ticket",
    ]
    event = {v: os.getenv(v) for v in variables}
    result = handler(event, None)
    client = boto3.client("stepfunctions")
    result_json = json.dumps(result, indent=4)
    tt = os.getenv("task_token", None)
    print(f" FUNCTION COMPLETED")
    # print(f" dumped result json \n", result_json)
    if tt:
        client.send_task_success(taskToken=os.environ["task_token"], output=result_json)
