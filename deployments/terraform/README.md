# Deploying Experiment Broker

This document describes how to deploy the Experiment Broker using Terraform.

## Prerequisites

- [Terraform CLI](https://developer.hashicorp.com/terraform/install)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

## Deployment Instructions

### CDK
TBD
### Terraform
There are two methods for deploying Experiment Broker through terraform. The first is to use the `terraform` CLI locally, and the second is to provision deploy the codepipeline infrastructure for deploying Experiment Broker through the AWS console.

You can run into issues with the first method depending on your OS, so the second method is recommended.

#### Experiment Broker Options
There are two variables that alter Experiment Broker's infrastructure darastically.

1. experiment_broker_deployment_type: Determines whether to deploy the Experiment Broker infrastructure using [Lambda Module](experiment_broker/modules/state_machine_lambda/) or [ECS Module](experiment_broker/modules/state_machine_ecs/) as the execution service.
2. chaos_toolkit_type: Determines whether to use [Chaos Toolkit](https://chaostoolkit.org/) or the [local version](/modules/chaos-toolkit-lite).

For details and restrictions on each, see variables.tf in either [experiment_broker](experiment_broker/variables.tf) or [experiment_broker_pipeline](experiment_broker_pipeline/variables.tf)

#### AWS Credentials
Before deploying Experiment Broker, you must configure your AWS credentials.

#### Setting Up Remote State Management
1. Clone the repository
2. Navigate to the `deployments/terraform/bootstrap` directory
3. Run the following commands:
```
terraform init
terraform validate
terraform plan
terraform apply
```
This will deploy the Experiment Broker provider infrastructure to your AWS environment, allowing state to be managed in the AWS environment.

#### Local Deployment
To deploy Experiment Broker Infrastructure to your AWS environment from your local machine:

1. Navigate to the `deployments/terraform/experiment-broker` directory
2. Run the following commands:
```
terraform init
terraform validate
terraform plan
terraform apply
```
This will deploy the Experiment Broker infrastructure to your AWS environment.

#### CodePipeline Deployment

To deploy Experiment Broker Infrastructure to your AWS environment from through AWS CodePipeline:

1. Navigate to the `deployments/terraform/experiment-broker` directory
2. Run the following commands:
```
terraform init
terraform validate
terraform plan
terraform apply
```
This will deploy the Experiment Broker CodePipeline infrastructure to your AWS environment.

3. Navigate to the AWS Console.
4. Navigate to CodeStar Connections.
5. Approve the connection, named 'experiment-broker-connection'. The connection is used to connect the CodePipeline to the GitHub repository. Ensure that the credentials used have access to the repository Experiment Broker is in.
6. Navigate to the CodePipeline service.
7. Click on the CodePipeline created, named 'experiment-broker-build-pipeline'.
8. Click on the 'Release Change' button to deploy the Experiment Broker infrastructure.
9. Manually Approve after the Plan stage is completed.

## Demo Instructions
**These instructions are for deploying the Experiment Broker demo, and assume you are using the 'demo' branch of this repository**

To deploy the Experiment Broker demo, navigate to the `deployments/terraform` directory and run the following commands:

```
./deploy_demo.sh
```

The script will deploy the Experiment Broker infrastructure to your AWS environment. It requires a manual action, which can be done through navigating to your AWS console, searching for codestar connections, finding `experiment-broker-connection`, and approving the connection. The connection is used to connect the CodePipeline to the GitHub repository. Ensure that the credentials used have access to the repository Experiment Broker is in.

To run the demo, in the same directory, run the following commands:

<pre><code>AWS_REGION=<i>your_aws_region</i> \
AWS_ACCOUNT=<i>your_aws_account</i> \
./run_demo.sh
</code></pre>
Replace *your_aws_region* and *your_aws_account* with your values for each.

This will run 3 demo experiments located in `deployments/terraform/experiment_broker/modules/s3_experiments_upload/experiments`.

Logs can be found by navigating to your AWS Console, accessing the Step Functions service, finding `experiment-broker-state-machine-lambda-demo`, and navigating to each of the executions.

## Cleanup Instructions For Experiment Broker Pipeline

To clean up the Experiment Broker infrastructure when deploying through CodePipeline:

1. Navigate to the CodePipeline service in the AWS Console.
2. Search for the pipeline named `experiment-broker-build-cleanup-pipeline`.
3. Run the pipeline, and approve the manual action.
4. Remediate any resources that were not deleted (such as emptying s3 buckets so they can be deleted).
5. Run the pipeline again, and approve the manual action.
6. Tear down the CodePipeline infrastructure by running the following commands in the `deployments/terraform/experiment_broker_pipeline` directory:
```
terraform destroy
```