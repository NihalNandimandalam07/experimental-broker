# Set the following environment variables:
# AWS_ACCOUNT
# AWS_REGION

execute_experiment () {
  sleep 1
  stop="False"
  while [ "$stop" == "False" ]; do

  execution_status=$(aws stepfunctions describe-execution --execution-arn $1 | jq -r '.status')

  echo "Current Execution Status: $execution_status"

  if [ "$execution_status" == "FAILED" ]; then
    echo "Experiment failed. Exiting..."
    exit 1
  elif [ "$execution_status" == "SUCCEEDED" ]; then
    echo "Experiment succeeded. Proceeding..."
    stop="True"
  fi

  if [ "$stop" == "False" ]; then
    echo "Waiting 15 seconds..."
    sleep 15
  fi

  done
}


set -e

if [ -z "$AWS_ACCOUNT" ]; then
  echo "Error running script, missing input for 'AWS_ACCOUNT'. Please execute the script following this example 'AWS_REGION=your_region AWS_ACCOUNT=your_account_id ./run_demo.sh'" 
  exit 1
elif [ -z "$AWS_REGION" ]; then
  echo "Error running script, missing input for 'AWS_REGION'. Please execute the script following this example 'AWS_REGION=your_region AWS_ACCOUNT_ID=your_account_id ./run_demo.sh'" 
  exit 1
fi 

set -e

EXPERIMENTS_BUCKET="experiment-broker-experiments-bucket-demo"
RESULTS_BUCKET="experiment-broker-experiment-results-bucket-demo"
STATE_MACHINE_ARN="arn:aws:states:${AWS_REGION}:${AWS_ACCOUNT}:stateMachine:experiment-broker-state-machine-lambda-demo"

echo "### Running EKS Network Latency Experiment ###"
execution_arn=$(aws stepfunctions start-execution --state-machine-arn $STATE_MACHINE_ARN --input "{\"Payload\":{\"list\":[{\"experiment_source\":\"Demo-Kubernetes(EKS)-Worker Node (EC2)-Network-Latency.yml\",\"bucket_name\":\"${EXPERIMENTS_BUCKET}\",\"output_path\":\"demo_journal_network_latency\",\"output_bucket\":\"${RESULTS_BUCKET}\"}],\"state\":\"pending\"}}" | jq -r '.executionArn')
execute_experiment "$execution_arn"

echo "### Running EKS Packet Loss Experiment ###"
execution_arn=$(aws stepfunctions start-execution --state-machine-arn $STATE_MACHINE_ARN --input "{\"Payload\":{\"list\":[{\"experiment_source\":\"Demo-Kubernetes(EKS)-Worker Node (EC2)-Network-PacketLoss.yml\",\"bucket_name\":\"${EXPERIMENTS_BUCKET}\",\"output_path\":\"demo_journal_packet_loss\",\"output_bucket\":\"${RESULTS_BUCKET}\"}],\"state\":\"pending\"}}" | jq -r '.executionArn')
execute_experiment "$execution_arn"

echo "### Running EKS State Termination Crash Experiment ###"
execution_arn=$(aws stepfunctions start-execution --state-machine-arn $STATE_MACHINE_ARN --input "{\"Payload\":{\"list\":[{\"experiment_source\":\"Demo-Kubernetes(EKS)-Worker Node (Pod)-State-TerminationCrash.yml\",\"bucket_name\":\"${EXPERIMENTS_BUCKET}\",\"output_path\":\"demo_journal_termination_crash\",\"output_bucket\":\"${RESULTS_BUCKET}\"}],\"state\":\"pending\"}}" | jq -r '.executionArn')
execute_experiment "$execution_arn"