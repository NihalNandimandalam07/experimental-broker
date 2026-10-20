mkdir build_temp
cp Dockerfile build_temp
cd build_temp

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

## Dockerfile Directory
DOCKERFILE_DIR=.

# Build Docker Image
docker build -t $ECR_REPOSITORY_NAME $DOCKERFILE_DIR --platform=linux/amd64
# Tag Docker Image
docker tag $ECR_REPOSITORY_NAME $ECR_REPOSITORY_NAME:latest
# Push Docker Image to ECR
docker push $ECR_REPOSITORY_NAME:latest
echo "Docker image pushed to ECR: $REPO_NAME"

cd ..
rm -r build_temp