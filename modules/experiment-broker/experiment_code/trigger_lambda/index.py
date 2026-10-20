import os, json, urllib3, uuid
from pprint import pprint
from create_execution import create_new_execution, authenticate

import boto3, logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


#{"experiment_source": "Demo-Kubernetes(EKS)-Worker Node (Pod)-State-TerminationCrash.yml",
#    "bucket_name": "resiliencyvr-package-build-bucket-demo",
#
#    "output_config": {
#        "S3": {
#            "bucket_name": "resiliencyvr-package-build-bucket-demo",
#            "path": "experiment_journals",
#        },
#    "jira_test_ticket": "XI-38",
#    "jira_exec_ticket":"XI-50"
#}}


def sample_input(experiments, jira_test_ticket):
    logger.info(experiments)
    bucket_name = os.getenv("BUCKET_NAME")
    input_prefix = os.getenv("EXPERIMENT_PREFIX")
    result_prefix = os.getenv("RESULT_PREFIX")
    base_dict = {"Payload":{"list": [],
                            "state": "pending"}}
    output_config = {"S3":{"bucket_name": bucket_name,
                            "path": result_prefix}}
                            
    token = authenticate()
    
    for experiment in experiments:
        event = {}
        event["bucket_name"] = bucket_name
        event["experiment_source"] = os.path.join(input_prefix, experiment)
        event["output_config"] = output_config
        event["jira_test_ticket"] = jira_test_ticket
        event["jira_exec_ticket"] = create_new_execution(jira_test_ticket, token)
        base_dict["Payload"]["list"].append(event)

    return base_dict

def lambda_handler(event, context):
    logger.info(event)
    experiments = [event.get("experiment_source")]

    sfn = boto3.client("stepfunctions")
    sma = os.getenv("STATE_MACHINE_ARN")
    description = sfn.describe_state_machine(stateMachineArn=sma)

    pprint(description)
    input = sample_input(experiments, event.get("jira_test_ticket"))
    print("State Machine Input :")
    pprint(input)
    start_info = sfn.start_execution(stateMachineArn=sma, input=json.dumps(input))
    print("State Machine Execution Info")
    pprint(start_info)