import boto3
import logging
import inspect
import json
import os

from traceback import format_exc
from logzero import logger
from time import sleep
from os import environ
from datetime import datetime, timedelta
from activities.ec2.shared import get_test_instance_ids
from activities.enums import ParameterMapFailuremode


def process_ssm_response(
    response: dict, ssm_params: dict, param_map_key: str = "default"
) -> dict:
    """Process SSM response and return more structured output"""

    try:
        failed = [x for x in response if x["status"] != "Success"]
        exec_details = {
            "ssm_document_full_name": ssm_params["DocumentName"],
            "parameter_map_key": param_map_key,
            "ssm_parameters": ssm_params,
            "execution_details": {
                "success": len(failed) == 0,
                "failed_count": len(failed),
                "response": response,
            },
        }
        if failed:
            logger.error(json.dumps(exec_details, default=str))
        else:
            logger.debug(json.dumps(exec_details, default=str))
        return exec_details

    except Exception as e:
        logger.error(e)
        logger.debug(response)


def get_ssm_status(ssm, command_id, max_duration):
    end_time = datetime.now() + timedelta(seconds=max_duration)
    current_status = ssm.list_command_invocations(CommandId=command_id, Details=True)[
        "CommandInvocations"
    ]
    while datetime.now() < end_time:
        while not current_status:
            logger.debug(f"""Command {command_id} not found, waiting""")
            sleep(2)
            current_status = current_status = ssm.list_command_invocations(
                CommandId=command_id, Details=True
            )["CommandInvocations"]

            incomplete = [
                x
                for x in current_status
                if x["Status"]
                not in [
                    "Success",
                    "Cancelled",
                    "TimedOut",
                    "Failed",
                ]
            ]
            logger.debug(
                f"""Instances not completed: { ','.join([x["InstanceId"] for x in incomplete])}"""
            )
            if not incomplete:
                logger.debug(f"""All Instances in SSM Run completed""")
                break
        results = [
            {
                "instanceid": x["InstanceId"],
                "status": x["Status"],
                "output": [
                    {
                        "stepname": y["Name"],
                        "output": y["Output"],
                        "responseCode": y.get("ResponseCode", None),
                        "status": y.get("Status", None),
                    }
                    for y in x["CommandPlugins"]
                ],
            }
            for x in current_status
        ]
        return results
    else:
        raise TimeoutError


def run_ssm_doc(
    document_name: str,
    test_instance_ids: list[str],
    doc_parameters: dict,
    region: str,
    cloudwatchconfig: dict = {},
    s3outputconfig: dict = {},
    check_delay: int = 10,
    max_duration: int = 600,
):
    end_time = datetime.now() + timedelta(seconds=max_duration)
    ssm_params = {
        "DocumentName": document_name,
        "InstanceIds": test_instance_ids,
        "CloudWatchOutputConfig": cloudwatchconfig,
        "Parameters": doc_parameters,
    }
    ssm_params.update(s3outputconfig)
    ssm_params.update(cloudwatchconfig)

    logger.info("""Starting SSM Run Command""")
    logger.debug(
        f"""Launching run of document: {document_name} with params: {json.dumps(doc_parameters)}"""
    )
    session = boto3.Session()
    ssm = session.client("ssm", region)
    response = ssm.send_command(**ssm_params)

    current_status = []
    incomplete = []
    command = response["Command"]
    logger.debug(f"""Command initiated with id: {command["InstanceIds"]}""")

    while datetime.now() < end_time:
        current_status = ssm.list_command_invocations(
            CommandId=command["CommandId"], Details=True
        )["CommandInvocations"]

        while not current_status:
            logger.debug(f"""Command {command["CommandId"]} not found, waiting""")
            sleep(2)
            current_status = current_status = ssm.list_command_invocations(
                CommandId=command["CommandId"], Details=True
            )["CommandInvocations"]

        incomplete = [
            x
            for x in current_status
            if x["Status"]
            not in [
                "Success",
                "Cancelled",
                "TimedOut",
                "Failed",
            ]
        ]
        logger.debug(
            f"""Instances not completed: { ','.join([x["InstanceId"] for x in incomplete])}"""
        )
        if not incomplete:
            logger.debug(f"""All Instances in SSM Run completed""")
            break
        sleep(check_delay)
    else:
        if incomplete:
            ids_to_cancel = [x["InstanceId"] for x in incomplete]
        logger.info(
            f"""Instances with incomplete runs at timeout, cancelling: {ids_to_cancel}"""
        )
        ssm.cancel_command(command["CommandId"], Details=True)["CommandInvocations"]
    results = [
        {
            "instanceid": x["InstanceId"],
            "status": x["Status"],
            "output": [
                {
                    "stepname": y["Name"],
                    "output": y["Output"],
                    "responseCode": y.get("ResponseCode", None),
                    "status": y.get("Status", None),
                }
                for y in x["CommandPlugins"]
            ],
        }
        for x in current_status
    ]
    return results


def run_ssm_doc_multistage(
    param_map: dict,
    def_instance_params: dict,
    def_doc_params: dict,
    doc_name: str,
    max_duration: int = 600,
    region: str = "us-east-1",
    failure_mode=ParameterMapFailuremode.FailFast,
    expanded_processing=True,
):
    """Handler to manage running multiple successive executions of the same SSM doc.

    Args:
        param_map (dict): _description_
        def_instance_params (dict): _description_
        def_doc_params (dict): _description_
        doc_name (str): _description_
        max_duration (int, optional): _description_. Defaults to 600.
        region (str, optional): _description_. Defaults to "us-east-1".
        failure_mode (_type_, optional): _description_. Defaults to ParameterMapFailuremode.FailFast.
        expanded_processing (bool, optional): _description_. Defaults to True.
    """
    _calling_func = inspect.stack()[1][3]
    results: list = []
    early_exit = False
    start_of_runs = datetime.now()
    last_run_duration = timedelta(seconds=0)

    for parameter_map_key, sev_params in param_map.items():
        if early_exit:
            results.append((parameter_map_key, "aborted", None))
            break
        expected_next_duration = datetime.now() - start_of_runs + last_run_duration
        if expected_next_duration.total_seconds() < max_duration:
            if not datetime.now() - start_of_runs + expected_next_duration < timedelta(
                seconds=max_duration
            ):
                logger.error(
                    f"{_calling_func}: ERROR Insufficient remaining run time to complete parameter_map_key {parameter_map_key}"
                )
                early_exit = True
                break
            step_start_time = datetime.now()
            logger.info(
                f"{_calling_func}: STARTING parameter_map_key {parameter_map_key}"
            )

            # merge parameters from sev_params into default params to create final parameters for stage execution
            # all parameters in sev_params must be a subset of the parames in the defaults
            step_doc_params = def_doc_params | {
                k: v for k, v in sev_params.items() if k in def_doc_params
            }
            step_instance_params = def_instance_params | {
                k: v for k, v in sev_params.items() if k in def_instance_params
            }

            test_instance_ids = get_test_instance_ids(
                test_target_type=step_instance_params.get("test_target_type", None),
                tag_key=step_instance_params.get("tag_key", None),
                tag_value=step_instance_params.get("tag_value", None),
                instance_ids=step_instance_params.get("instance_ids", None),
                region=step_instance_params.get("region", None),
            )

            try:
                run_results = run_ssm_doc(
                    document_name=doc_name,
                    test_instance_ids=test_instance_ids,
                    doc_parameters=step_doc_params,
                    region=region,
                )
                if not expanded_processing:
                    failed = [x for x in run_results if x["status"] != "Success"]
                    if failed:
                        for failure in failed:
                            output = ";".join([x["output"] for x in failure["output"]])
                            logger.error(
                                f"{failed['instanceid']} failed in ssm execution with output: {output}"
                            )
                            results.append((parameter_map_key, "failed", run_results))
                            if failure_mode is ParameterMapFailuremode.FailFast:
                                early_exit = True
                                break
                    results.append((parameter_map_key, "success", run_results))
            except Exception as e:
                logger.error(e)
                err = format_exc()
                try:
                    results.append((parameter_map_key, "failed", run_results))
                except NameError:
                    results.append((parameter_map_key, "failed", err))
            last_run_duration = datetime.now() - step_start_time
    return results
