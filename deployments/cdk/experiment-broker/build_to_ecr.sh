#!/usr/bin/env bash
# AWS Region
AWS_REGION="us-east-1"
# AWS Account ID
AWS_ACCOUNT_ID="899456967600"
# AWS ECR Login
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

python_path=$(which python)

mkdir build
python -m build --wheel --outdir build ../../Experiment-Broker-Module/experiment_code
python -m build --wheel --outdir build ../../vr-regression-testing

cp ../../Experiment-Broker-Module/experiment_code/lambda/handler.py ./build/

## ECR Repository Name
REPO_NAME="eb-test-payload-processor"
## Dockerfile Directory
# DOCKERFILE_DIR=../../Experiment-Broker-Module/experiment_code
DOCKERFILE_DIR=.


# Build Docker Image
docker build -t $REPO_NAME $DOCKERFILE_DIR --platform=linux/amd64
# Tag Docker Image
docker tag $REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest
# Push Docker Image to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest
echo "Docker image pushed to ECR: $REPO_NAME"

