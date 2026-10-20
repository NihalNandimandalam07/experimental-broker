#!/usr/bin/env bash

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="001002003004"

mkdir ecs_build_temp

python -m venv venv --copies

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

venv/bin/python -m pip install build

venv/bin/python -m build --wheel --outdir ecs_build_temp ../../Experiment-Broker-Modules/experiment_code
venv/bin/python -m build --wheel --outdir ecs_build_temp ../../chaos-toolkit-lite
venv/bin/python -m build --wheel --outdir ecs_build_temp ../../Experiment-Broker-Logging-Module

cp ../../Experiment-Broker-Module/experiment_code/lambda/handler.py ecs_build_temp
cp ../../Experiment-Broker-Module/experiment_code/activities/requirements.txt ecs_build_temp

ls -lah
ls -lah ecs_build_temp

REPO_NAME="eb-test-payload-processor"

DOCKERFILE_DIR=.

docker build -t $REPO_NAME $DOCKERFILE_DIR --platform=linux/amd64

docker tag $REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest

docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest

echo "Docker image pushed to ECR: $REPO_NAME"