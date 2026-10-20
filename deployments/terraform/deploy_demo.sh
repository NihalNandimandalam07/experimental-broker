# This is a script to automate the deployment of the infrastructure using Terraform, and CLI commands to trigger the CodePipeline
# Set the following environment variables: 

set -e

cd bootstrap

echo "Setting up terraform remote backend"
echo "Running terraform init..."
terraform init
echo "Running terraform apply..."
terraform apply -auto-approve -var-file="demo.tfvars"

cd ../experiment_broker_pipeline

echo "Setting up experiment broker pipeline deployment"

STAGE_NAME="Approve"
ACTION_NAME="Approve"
CONNECTION_NAME=$(grep "^codestar_connection_name" "default.auto.tfvars" | cut -d'=' -f2 | sed 's/"//g' | awk '{$1=$1;print}')
PIPELINE_NAME=$(grep "^build_pipeline_name" "demo.tfvars" | cut -d'=' -f2 | sed 's/"//g' | awk '{$1=$1;print}')
echo "Found codestar connection name: $CONNECTION_NAME"
echo "Found build pipeline name: $PIPELINE_NAME"

echo "Running terraform init..."
terraform init
echo "Running terraform apply..."
terraform apply -auto-approve -var-file="demo.tfvars"

echo "Waiting for CodeStar Connection to be authenticated..."
echo "Please authenticate the CodeStar Connection by following this documentation. This can only be done manually through console."
echo "https://docs.aws.amazon.com/dtconsole/latest/userguide/connections-update.html"

while true; do
  STATUS=$(aws codestar-connections list-connections --query "Connections[?ConnectionName=='$CONNECTION_NAME'].ConnectionStatus" --output text)
  
  if [ "$STATUS" == "AVAILABLE" ]; then
    echo "Connection status reached expected value of 'AVAILABLE'. continuing..."
    break
  elif [ "$STATUS" == "PENDING" ]; then
    echo "Connection status is still 'PENDING'. Checking again in 15 seconds..."
  else
    echo "Connection status is not 'AVAILABLE' or 'PENDING'. Please remediate. exiting..."
    exit 1
  fi

  sleep 15
done

echo "Pipeline deployment completed."
echo "Triggering CodePipeline to deploy the application..."
execution_id=$(aws codepipeline start-pipeline-execution --name $PIPELINE_NAME | jq -r '.pipelineExecutionId')

# echo "$execution_id"

sleep 10

apply_successful="False"
while [ "$apply_successful" == "False" ]; do
  pipeline_state=$(aws codepipeline get-pipeline-state --name "$PIPELINE_NAME")

  # echo "$pipeline_state"

  failed=$(echo "$pipeline_state" | jq -r --arg execution_id "$execution_id" '
    .stageStates[] | select(.latestExecution.status == "Failed" and .latestExecution.pipelineExecutionId == $execution_id) |
    .actionStates[] | select(.latestExecution.status == "Failed") |
    .actionName
  ')

  # echo "$failed"

  if [ -n "$failed" ]; then
    echo "Pipeline execution failed. Please remediate. Exiting..."
    exit 1
  fi

  echo "Checking current in-progress step..."
  in_progress_step=$(echo "$pipeline_state" | jq -r --arg execution_id "$execution_id" '
    .stageStates[] | select(.latestExecution.status == "InProgress" and .latestExecution.pipelineExecutionId == $execution_id) | 
    .actionStates[] | select(.latestExecution.status == "InProgress") | 
    .actionName
  ')

  echo "Current in-progress step: $in_progress_step"

  if [ "$in_progress_step" == "$ACTION_NAME" ]; then
    token=$(echo "$pipeline_state" | jq -r --arg STAGE_NAME "$STAGE_NAME" --arg ACTION_NAME "$ACTION_NAME" '
      .stageStates[] | select(.stageName == $STAGE_NAME) | 
      .actionStates[] | select(.actionName == $ACTION_NAME) | 
      .latestExecution.token
    ')
    echo "Approved the manual approval step..."
    aws codepipeline put-approval-result --pipeline-name "$PIPELINE_NAME" --stage-name "$STAGE_NAME" --action-name "$ACTION_NAME" --result summary="Approved",status="Approved" --token "$token"
  fi

  sleep 15
  echo "Sleeping 15 seconds..."
  pipeline_status=$(echo "$pipeline_state" | jq -r '.stageStates[-1].latestExecution.status')
  if [[ "$pipeline_status" == *"Succeeded"* ]]; then
    echo "Apply has been successful."
    apply_successful="True"
  fi
done