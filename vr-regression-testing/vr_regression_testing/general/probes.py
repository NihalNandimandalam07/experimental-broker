import time, os
import logging
import boto3
from chaoslib.exceptions import ActivityFailed
from vr_regression_testing.general.shared import get_ssm_parameter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_most_recent_running_execution_arn(sfn_arn: str, client: boto3.client):

    try:
        response = client.list_executions(stateMachineArn=sfn_arn, maxResults=1, statusFilter='RUNNING')
        executions = response['executions']

        if executions:
            return executions[0]['executionArn']
            
        else:
            logger.info("No executions found for the given state machine ARN.")
            return None

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        return None
    

def identify_sfn_execution(retry_num: int, retry_interval: int=5):
    if 'CURRENT_EXECUTION_ARN' in os.environ:
        logging.info(f"CURRENT_EXECUTION_ARN already present. Value is {os.getenv('CURRENT_EXECUTION_ARN')}")
        return True
      
    if 'JOB_ID' in os.environ:
        job_id = os.getenv('JOB_ID')
        client = boto3.client('stepfunctions')

        sfn_arn = os.getenv('CURRENT_SFN_ARN')


        most_recent_exec = get_most_recent_running_execution_arn(sfn_arn, client)
        retries=0
        while not most_recent_exec and retries<retry_num:
            logger.info(f"Retrying identification in {retry_interval}s...")
            time.sleep(retry_interval)
            most_recent_exec = get_most_recent_running_execution_arn(sfn_arn, client)
            retries += 1

        if most_recent_exec:
            logger.info(f"Identified: {most_recent_exec}")
            os.environ["CURRENT_EXECUTION_ARN"] = most_recent_exec
            return True
        else:
            return False
    else:
        logging.info("No JOB_ID. Retry later...")
        return True # no job id, wait

def describe_sfn_execution(target_exec_arn:str, client: boto3.client):
    try:
        execution_details = client.describe_execution(executionArn=target_exec_arn)
        return execution_details

    except client.exceptions.ExecutionDoesNotExist as e:
        error_log = f"Execution with ARN '{target_exec_arn}' not found."
        logger.error(error_log)
        raise ActivityFailed(error_log)    


    except Exception as e:
        logger.error(f"Error occurred: {e}")
        raise ActivityFailed(e)

def evaluate_sfn_status(target_exec_arn:str , retry_interval: int=30):
    client = boto3.client('stepfunctions')

    execution_details = describe_sfn_execution(target_exec_arn, client)
    execution_status = execution_details['status']
    logger.info(f"Evaluating execution. Current State: {execution_status}")

    while execution_status == 'RUNNING':
        execution_details = describe_sfn_execution(target_exec_arn, client)
        execution_status = execution_details['status']
        if execution_status == 'RUNNING':
            logger.info(f"Execution is still running. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)
        elif execution_status == 'SUCCEEDED':

            os.environ.pop('CURRENT_EXECUTION_ARN', None) # reset
            os.environ["EXECUTION_STATUS"] = execution_status

            return True
        else:
            logging.error(f"Failing execution status: {execution_status}")
            return False
        
def watch_sfn_execution(retry_interval: int=30):
    if 'CURRENT_EXECUTION_ARN' in os.environ:
        curr_exec = os.getenv('CURRENT_EXECUTION_ARN')
        return evaluate_sfn_status(curr_exec)
    else:
        logging.info("No env var for CURRENT_EXECUTION_ARN. Retry later...")
        return True 



