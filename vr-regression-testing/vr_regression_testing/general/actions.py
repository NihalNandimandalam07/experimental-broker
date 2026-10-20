
import os, time, json

import boto3
import logging
from botocore.exceptions import ClientError
from chaoslib.exceptions import ActivityFailed

from vr_regression_testing.general.shared import get_ssm_parameter


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def copy_object_s3(source_bucket: str, source_key: str, target_bucket: str):
    s3 = boto3.client('s3')
    try:
        s3.copy_object(
            Bucket=target_bucket,
            CopySource={'Bucket': source_bucket, 'Key': source_key},
            Key=source_key
        )
        logger.info(f"Object {source_key} copied from {source_bucket} to {target_bucket}")
        os.environ["JOB_ID"] = "TEST"

        first_sfn_param = "Wait"
        os.environ["CURRENT_SFN_ARN"] = get_ssm_parameter(f'/RegressionTesting/StateMachineArns/{first_sfn_param}')

        return True
    except ClientError as e:
        error_log = f"Error copying object {source_key} from {source_bucket} to {target_bucket}: {e}"
        logger.error(error_log)
        raise ActivityFailed(error_log)

def block_until_complete(watch_var: str='EXECUTION_STATUS', retry_interval: int = 15, max_retries: int = 100):
    retries = 0
    while retries < max_retries:
        if watch_var in os.environ:
            if os.environ[watch_var] == "SUCCEEDED":
                os.environ.pop(watch_var, None) # reset
                return True
        retries += 1
        time.sleep(retry_interval)
    error_log = f"Retry limit reached"
    logger.error(error_log)

    raise ActivityFailed(error_log)


def initiate_next_sfn(next_sfn_param: str):
       
    try:
        sfn_arn = get_ssm_parameter(f'/RegressionTesting/StateMachineArns/{next_sfn_param}')
        client = boto3.client('stepfunctions')

        payload = None # necessary?

        response = client.start_execution(
            stateMachineArn=sfn_arn,
            input=json.dumps(payload) if payload else '{}'
        )

        execution_arn = response['executionArn']

        os.environ["CURRENT_SFN_ARN"]=sfn_arn
        os.environ["CURRENT_EXECUTION_ARN"]=execution_arn

    except Exception as e:
        print("Error:", e)
        raise ActivityFailed("Error:", e)

def sfn_handoff(next_sfn_param: str, wait_watch_var: str='EXECUTION_STATUS', wait_retry_interval: int = 15, wait_max_retries: int = 100):
    block_until_complete(wait_watch_var, wait_retry_interval, wait_max_retries)
    initiate_next_sfn(next_sfn_param)

