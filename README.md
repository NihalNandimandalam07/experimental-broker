# AWS Resiliency Module Pipeline Repository

This is the AWS CDK CI/CD Pipeline repository for Vertical Relevance's AWS Resiliency Module. This repository consists of two CDK codebases that will deploy two separate CodePipelines. The PackagePipeline directory has CDK code that will build the resiliencyvr Python package and upload it to CodeArtifact. This package is a requirement for the resiliency execution Lambda, so it must be deployed first. The LambdaPipeline has CDK code that will deploy the resiliency execution Lambda. Deploy the LambdaPipeline CDK after ResiliencyPipeline.

## Prior to starting the setup of the CDK environment, ensure that you have cloned this repo and installed v2.28.0 of the CDK cli tool. 

## Follow the setup steps below to properly configure the environment and first deployment of the infrastructure.

Create a Python virtualenv using the tool of your choice.
To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are on a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

## Deploy the CDK
### Run the below commands in PackagePipeline, then in LambdaPipeline
Navigate to the pipeline dir.

```
cd pipeline_infra
```

Bootstrap the cdk app.

```
cdk bootstrap
```

At this point you can deploy the CDK app for this blueprint.

```
$ cdk deploy --all
```
IAM Statement Changes needed to deploy the stacks
```
IAM Statement Changes
┌───┬───────────────────────────────────────────────┬────────┬───────────────────────────────────────────────┬───────────────────────────────────────────────┬─────────────────────────────────────────────────┐
│   │ Resource                                      │ Effect │ Action                                        │ Principal                                     │ Condition                                       │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${Custom::S3AutoDeleteObjectsCustomResourcePr │ Allow  │ sts:AssumeRole                                │ Service:lambda.amazonaws.com                  │                                                 │
│   │ ovider/Role.Arn}                              │        │                                               │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${MyCfnDomain.Arn}                            │ Allow  │ codeartifact:PublishPackageVersion            │ AWS:*                                         │                                                 │
│ + │ ${MyCfnDomain.Arn}                            │ Allow  │ codeartifact:DescribePackageVersion           │ AWS:*                                         │                                                 │
│   │                                               │        │ codeartifact:DescribeRepository               │                                               │                                                 │
│   │                                               │        │ codeartifact:GetAuthorizationToken            │                                               │                                                 │
│   │                                               │        │ codeartifact:GetPackageVersionReadme          │                                               │                                                 │
│   │                                               │        │ codeartifact:GetRepositoryEndpoint            │                                               │                                                 │
│   │                                               │        │ codeartifact:ListPackageVersionAssets         │                                               │                                                 │
│   │                                               │        │ codeartifact:ListPackageVersionDependencies   │                                               │                                                 │
│   │                                               │        │ codeartifact:ListPackageVersions              │                                               │                                                 │
│   │                                               │        │ codeartifact:ListPackages                     │                                               │                                                 │
│   │                                               │        │ codeartifact:ReadFromRepository               │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${MyCfnDomain.Arn}                            │ Allow  │ codeartifact:GetAuthorizationToken            │ AWS:${resiliencyvr_codebuild_package_role}    │                                                 │
│   │ ${MyCfnDomain.Arn}/*                          │        │ codeartifact:GetRepositoryEndpoint            │                                               │                                                 │
│   │ ${cfn_repository_res_ca_dev.Arn}              │        │                                               │                                               │                                                 │
│ + │ ${MyCfnDomain.Arn}                            │ Allow  │ codeartifact:GetAuthorizationToken            │ AWS:${resiliencyvr_codebuild_lambda_role}     │                                                 │
│   │ ${MyCfnDomain.Arn}/*                          │        │ codeartifact:GetRepositoryEndpoint            │                                               │                                                 │
│   │ ${cfn_repository_res_ca_dev.Arn}              │        │                                               │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${cdk_deploy_demo.Arn}                             │ Allow  │ codebuild:BatchGetBuilds                      │ AWS:${lambda_pipeline/Deploy/Deploy/CodePipel │                                                 │
│   │                                               │        │ codebuild:StartBuild                          │ ineActionRole}                                │                                                 │
│   │                                               │        │ codebuild:StopBuild                           │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${code_pipeline_bucket.Arn}                   │ Allow  │ s3:Abort*                                     │ AWS:${resiliencyvr_codebuild_package_role}    │                                                 │
│   │ ${code_pipeline_bucket.Arn}/*                 │        │ s3:DeleteObject*                              │                                               │                                                 │
│   │                                               │        │ s3:PutObject                                  │                                               │                                                 │
│   │                                               │        │ s3:PutObjectLegalHold                         │                                               │                                                 │
│   │                                               │        │ s3:PutObjectRetention                         │                                               │                                                 │
│   │                                               │        │ s3:PutObjectTagging                           │                                               │                                                 │
│   │                                               │        │ s3:PutObjectVersionTagging                    │                                               │                                                 │
│ + │ ${code_pipeline_bucket.Arn}                   │ Allow  │ s3:DeleteObject*                              │ AWS:${Custom::S3AutoDeleteObjectsCustomResour │                                                 │
│   │ ${code_pipeline_bucket.Arn}/*                 │        │ s3:GetBucket*                                 │ ceProvider/Role.Arn}                          │                                                 │
│   │                                               │        │ s3:List*                                      │                                               │                                                 │
│ + │ ${code_pipeline_bucket.Arn}                   │ Allow  │ s3:GetBucketVersioning                        │ AWS:${resiliencyvr-package-build-pipeline-rol │                                                 │
│   │ ${code_pipeline_bucket.Arn}/*                 │        │ s3:GetObject                                  │ e}                                            │                                                 │
│   │                                               │        │ s3:GetObjectVersion                           │                                               │                                                 │
│   │                                               │        │ s3:PutObject                                  │                                               │                                                 │
│   │                                               │        │ s3:PutObjectAcl                               │                                               │                                                 │
│ + │ ${code_pipeline_bucket.Arn}                   │ Allow  │ s3:GetBucketVersioning                        │ AWS:${resiliencyvr_codebuild_package_role}    │                                                 │
│   │ ${code_pipeline_bucket.Arn}/*                 │        │ s3:GetObject                                  │                                               │                                                 │
│   │                                               │        │ s3:GetObjectVersion                           │                                               │                                                 │
│   │                                               │        │ s3:PutObject                                  │                                               │                                                 │
│   │                                               │        │ s3:PutObjectAcl                               │                                               │                                                 │
│ + │ ${code_pipeline_bucket.Arn}                   │ Allow  │ s3:GetBucketVersioning                        │ AWS:${resiliencyvr_codebuild_lambda_role}     │                                                 │
│   │ ${code_pipeline_bucket.Arn}/*                 │        │ s3:GetObject                                  │                                               │                                                 │
│   │                                               │        │ s3:GetObjectVersion                           │                                               │                                                 │
│   │                                               │        │ s3:PutObject                                  │                                               │                                                 │
│   │                                               │        │ s3:PutObjectAcl                               │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${lambda_pipeline/ArtifactsBucket.Arn}        │ Allow  │ s3:GetBucket*                                 │ AWS:${resiliencyvr_codebuild_lambda_role}     │                                                 │
│   │ ${lambda_pipeline/ArtifactsBucket.Arn}/*      │        │ s3:GetObject*                                 │                                               │                                                 │
│   │                                               │        │ s3:List*                                      │                                               │                                                 │
│ + │ ${lambda_pipeline/ArtifactsBucket.Arn}        │ Deny   │ s3:*                                          │ AWS:*                                         │ "Bool": {                                       │
│   │ ${lambda_pipeline/ArtifactsBucket.Arn}/*      │        │                                               │                                               │   "aws:SecureTransport": "false"                │
│   │                                               │        │                                               │                                               │ }                                               │
│ + │ ${lambda_pipeline/ArtifactsBucket.Arn}        │ Allow  │ s3:Abort*                                     │ AWS:${lambda_pipeline/Role}                   │                                                 │
│   │ ${lambda_pipeline/ArtifactsBucket.Arn}/*      │        │ s3:DeleteObject*                              │                                               │                                                 │
│   │                                               │        │ s3:GetBucket*                                 │                                               │                                                 │
│   │                                               │        │ s3:GetObject*                                 │                                               │                                                 │
│   │                                               │        │ s3:List*                                      │                                               │                                                 │
│   │                                               │        │ s3:PutObject                                  │                                               │                                                 │
│   │                                               │        │ s3:PutObjectLegalHold                         │                                               │                                                 │
│   │                                               │        │ s3:PutObjectRetention                         │                                               │                                                 │
│   │                                               │        │ s3:PutObjectTagging                           │                                               │                                                 │
│   │                                               │        │ s3:PutObjectVersionTagging                    │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${lambda_pipeline/ArtifactsBucketEncryptionKe │ Allow  │ kms:*                                         │ AWS:arn:${AWS::Partition}:iam::${AWS::Account │                                                 │
│   │ y.Arn}                                        │        │                                               │ Id}:root                                      │                                                 │
│ + │ ${lambda_pipeline/ArtifactsBucketEncryptionKe │ Allow  │ kms:Decrypt                                   │ AWS:${resiliencyvr_codebuild_lambda_role}     │                                                 │
│   │ y.Arn}                                        │        │ kms:DescribeKey                               │                                               │                                                 │
│ + │ ${lambda_pipeline/ArtifactsBucketEncryptionKe │ Allow  │ kms:Decrypt                                   │ AWS:${resiliencyvr_codebuild_lambda_role}     │                                                 │
│   │ y.Arn}                                        │        │ kms:Encrypt                                   │                                               │                                                 │
│   │                                               │        │ kms:GenerateDataKey*                          │                                               │                                                 │
│   │                                               │        │ kms:ReEncrypt*                                │                                               │                                                 │
│ + │ ${lambda_pipeline/ArtifactsBucketEncryptionKe │ Allow  │ kms:Decrypt                                   │ AWS:${lambda_pipeline/Role}                   │                                                 │
│   │ y.Arn}                                        │        │ kms:DescribeKey                               │                                               │                                                 │
│   │                                               │        │ kms:Encrypt                                   │                                               │                                                 │
│   │                                               │        │ kms:GenerateDataKey*                          │                                               │                                                 │
│   │                                               │        │ kms:ReEncrypt*                                │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${lambda_pipeline/Deploy/Deploy/CodePipelineA │ Allow  │ sts:AssumeRole                                │ AWS:arn:${AWS::Partition}:iam::${AWS::Account │                                                 │
│   │ ctionRole.Arn}                                │        │                                               │ Id}:root                                      │                                                 │
│ + │ ${lambda_pipeline/Deploy/Deploy/CodePipelineA │ Allow  │ sts:AssumeRole                                │ AWS:${lambda_pipeline/Role}                   │                                                 │
│   │ ctionRole.Arn}                                │        │                                               │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${lambda_pipeline/Role.Arn}                   │ Allow  │ sts:AssumeRole                                │ Service:codepipeline.amazonaws.com            │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${res-ca-dev-repo-key-demo.Arn}                    │ Allow  │ kms:*                                         │ AWS:arn:${AWS::Partition}:iam::${AWS::Account │                                                 │
│   │                                               │        │                                               │ Id}:root                                      │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${resiliencyvr_codebuild_lambda_role.Arn}     │ Allow  │ sts:AssumeRole                                │ Service:codebuild.amazonaws.com               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${resiliencyvr_codebuild_package_role.Arn}    │ Allow  │ sts:AssumeRole                                │ Service:codebuild.amazonaws.com               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${resiliencyvr_codebuild_project_demo.Arn}         │ Allow  │ codebuild:BatchGetBuilds                      │ AWS:${resiliencyvr_pipeline/Build/Build/CodeP │                                                 │
│   │                                               │        │ codebuild:StartBuild                          │ ipelineActionRole}                            │                                                 │
│   │                                               │        │ codebuild:StopBuild                           │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${resiliencyvr-package-build-pipeline-role.Ar │ Allow  │ sts:AssumeRole                                │ Service:codepipeline.amazonaws.com            │                                                 │
│   │ n}                                            │        │                                               │                                               │                                                 │
│ + │ ${resiliencyvr-package-build-pipeline-role.Ar │ Allow  │ sts:AssumeRole                                │ Service:codebuild.amazonaws.com               │                                                 │
│   │ n}                                            │        │                                               │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${resiliencyvr_pipeline/ArtifactsBucket.Arn}  │ Allow  │ s3:GetBucket*                                 │ AWS:${resiliencyvr_codebuild_package_role}    │                                                 │
│   │ ${resiliencyvr_pipeline/ArtifactsBucket.Arn}/ │        │ s3:GetObject*                                 │                                               │                                                 │
│   │ *                                             │        │ s3:List*                                      │                                               │                                                 │
│ + │ ${resiliencyvr_pipeline/ArtifactsBucket.Arn}  │ Deny   │ s3:*                                          │ AWS:*                                         │ "Bool": {                                       │
│   │ ${resiliencyvr_pipeline/ArtifactsBucket.Arn}/ │        │                                               │                                               │   "aws:SecureTransport": "false"                │
│   │ *                                             │        │                                               │                                               │ }                                               │
│ + │ ${resiliencyvr_pipeline/ArtifactsBucket.Arn}  │ Allow  │ s3:Abort*                                     │ AWS:${resiliencyvr_pipeline/Role}             │                                                 │
│   │ ${resiliencyvr_pipeline/ArtifactsBucket.Arn}/ │        │ s3:DeleteObject*                              │                                               │                                                 │
│   │ *                                             │        │ s3:GetBucket*                                 │                                               │                                                 │
│   │                                               │        │ s3:GetObject*                                 │                                               │                                                 │
│   │                                               │        │ s3:List*                                      │                                               │                                                 │
│   │                                               │        │ s3:PutObject                                  │                                               │                                                 │
│   │                                               │        │ s3:PutObjectLegalHold                         │                                               │                                                 │
│   │                                               │        │ s3:PutObjectRetention                         │                                               │                                                 │
│   │                                               │        │ s3:PutObjectTagging                           │                                               │                                                 │
│   │                                               │        │ s3:PutObjectVersionTagging                    │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${resiliencyvr_pipeline/ArtifactsBucketEncryp │ Allow  │ kms:*                                         │ AWS:arn:${AWS::Partition}:iam::${AWS::Account │                                                 │
│   │ tionKey.Arn}                                  │        │                                               │ Id}:root                                      │                                                 │
│ + │ ${resiliencyvr_pipeline/ArtifactsBucketEncryp │ Allow  │ kms:Decrypt                                   │ AWS:${resiliencyvr_codebuild_package_role}    │                                                 │
│   │ tionKey.Arn}                                  │        │ kms:DescribeKey                               │                                               │                                                 │
│ + │ ${resiliencyvr_pipeline/ArtifactsBucketEncryp │ Allow  │ kms:Decrypt                                   │ AWS:${resiliencyvr_codebuild_package_role}    │                                                 │
│   │ tionKey.Arn}                                  │        │ kms:Encrypt                                   │                                               │                                                 │
│   │                                               │        │ kms:GenerateDataKey*                          │                                               │                                                 │
│   │                                               │        │ kms:ReEncrypt*                                │                                               │                                                 │
│ + │ ${resiliencyvr_pipeline/ArtifactsBucketEncryp │ Allow  │ kms:Decrypt                                   │ AWS:${resiliencyvr_pipeline/Role}             │                                                 │
│   │ tionKey.Arn}                                  │        │ kms:DescribeKey                               │                                               │                                                 │
│   │                                               │        │ kms:Encrypt                                   │                                               │                                                 │
│   │                                               │        │ kms:GenerateDataKey*                          │                                               │                                                 │
│   │                                               │        │ kms:ReEncrypt*                                │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${resiliencyvr_pipeline/Build/Build/CodePipel │ Allow  │ sts:AssumeRole                                │ AWS:arn:${AWS::Partition}:iam::${AWS::Account │                                                 │
│   │ ineActionRole.Arn}                            │        │                                               │ Id}:root                                      │                                                 │
│ + │ ${resiliencyvr_pipeline/Build/Build/CodePipel │ Allow  │ sts:AssumeRole                                │ AWS:${resiliencyvr_pipeline/Role}             │                                                 │
│   │ ineActionRole.Arn}                            │        │                                               │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ ${resiliencyvr_pipeline/Role.Arn}             │ Allow  │ sts:AssumeRole                                │ Service:codepipeline.amazonaws.com            │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ *                                             │ Allow  │ logs:CreateLogGroup                           │ AWS:${resiliencyvr_codebuild_package_role}    │                                                 │
│   │                                               │        │ logs:CreateLogStream                          │                                               │                                                 │
│   │                                               │        │ logs:PutLogEvents                             │                                               │                                                 │
│ + │ *                                             │ Allow  │ sts:GetServiceBearerToken                     │ AWS:${resiliencyvr_codebuild_package_role}    │                                                 │
│ + │ *                                             │ Allow  │ cloudformation:DescribeStacks                 │ AWS:${resiliencyvr_codebuild_lambda_role}     │                                                 │
│   │                                               │        │ codepipeline:GetPipeline                      │                                               │                                                 │
│   │                                               │        │ codepipeline:GetPipelineState                 │                                               │                                                 │
│   │                                               │        │ logs:CreateLogGroup                           │                                               │                                                 │
│   │                                               │        │ logs:CreateLogStream                          │                                               │                                                 │
│   │                                               │        │ logs:PutLogEvents                             │                                               │                                                 │
│   │                                               │        │ ssm:GetParameter                              │                                               │                                                 │
│   │                                               │        │ sts:GetServiceBearerToken                     │                                               │                                                 │
│ + │ *                                             │ Allow  │ lambda:ListAliases                            │ AWS:${resiliencyvr_codebuild_lambda_role}     │                                                 │
│   │                                               │        │ lambda:ListCodeSigningConfigs                 │                                               │                                                 │
│   │                                               │        │ lambda:ListEventSourceMappings                │                                               │                                                 │
│   │                                               │        │ lambda:ListFunctionEventInvokeConfigs         │                                               │                                                 │
│   │                                               │        │ lambda:ListFunctionUrlConfigs                 │                                               │                                                 │
│   │                                               │        │ lambda:ListFunctions                          │                                               │                                                 │
│   │                                               │        │ lambda:ListFunctionsByCodeSigningConfig       │                                               │                                                 │
│   │                                               │        │ lambda:ListLayerVersions                      │                                               │                                                 │
│   │                                               │        │ lambda:ListLayers                             │                                               │                                                 │
│   │                                               │        │ lambda:ListProvisionedConcurrencyConfigs      │                                               │                                                 │
│   │                                               │        │ lambda:ListTags                               │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ arn:${AWS::Partition}:codebuild:${AWS::Region │ Allow  │ codebuild:BatchPutCodeCoverages               │ AWS:${resiliencyvr_codebuild_lambda_role}     │                                                 │
│   │ }:${AWS::AccountId}:report-group/${cdkdeploy2 │        │ codebuild:BatchPutTestCases                   │                                               │                                                 │
│   │ BDC7964}-*                                    │        │ codebuild:CreateReport                        │                                               │                                                 │
│   │                                               │        │ codebuild:CreateReportGroup                   │                                               │                                                 │
│   │                                               │        │ codebuild:UpdateReport                        │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ arn:${AWS::Partition}:codebuild:${AWS::Region │ Allow  │ codebuild:BatchPutCodeCoverages               │ AWS:${resiliencyvr_codebuild_package_role}    │                                                 │
│   │ }:${AWS::AccountId}:report-group/${resiliency │        │ codebuild:BatchPutTestCases                   │                                               │                                                 │
│   │ vrcodebuildproject7F264C94}-*                 │        │ codebuild:CreateReport                        │                                               │                                                 │
│   │                                               │        │ codebuild:CreateReportGroup                   │                                               │                                                 │
│   │                                               │        │ codebuild:UpdateReport                        │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ arn:${AWS::Partition}:logs:${AWS::Region}:${A │ Allow  │ logs:CreateLogGroup                           │ AWS:${resiliencyvr_codebuild_lambda_role}     │                                                 │
│   │ WS::AccountId}:log-group:/aws/codebuild/${cdk │        │ logs:CreateLogStream                          │                                               │                                                 │
│   │ deploy2BDC7964}                               │        │ logs:PutLogEvents                             │                                               │                                                 │
│   │ arn:${AWS::Partition}:logs:${AWS::Region}:${A │        │                                               │                                               │                                                 │
│   │ WS::AccountId}:log-group:/aws/codebuild/${cdk │        │                                               │                                               │                                                 │
│   │ deploy2BDC7964}:*                             │        │                                               │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ arn:${AWS::Partition}:logs:${AWS::Region}:${A │ Allow  │ logs:CreateLogGroup                           │ AWS:${resiliencyvr_codebuild_package_role}    │                                                 │
│   │ WS::AccountId}:log-group:/aws/codebuild/${res │        │ logs:CreateLogStream                          │                                               │                                                 │
│   │ iliencyvrcodebuildproject7F264C94}            │        │ logs:PutLogEvents                             │                                               │                                                 │
│   │ arn:${AWS::Partition}:logs:${AWS::Region}:${A │        │                                               │                                               │                                                 │
│   │ WS::AccountId}:log-group:/aws/codebuild/${res │        │                                               │                                               │                                                 │
│   │ iliencyvrcodebuildproject7F264C94}:*          │        │                                               │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ arn:aws:codebuild:${AWS::Region}:${AWS::Accou │ Allow  │ codebuild:BatchGetBuilds                      │ AWS:${resiliencyvr-package-build-pipeline-rol │                                                 │
│   │ ntId}:project/resiliencyvr-package-codebuild  │        │ codebuild:StartBuild                          │ e}                                            │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ arn:aws:codestar-connections:region:account-i │ Allow  │ codestar-connections:UseConnection            │ AWS:${resiliencyvr-package-build-pipeline-rol │                                                 │
│   │ d:connection/connection-id                    │        │                                               │ e}                                            │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ arn:aws:iam::${AWS::AccountId}:role/cdk-*-dep │ Allow  │ iam:PassRole                                  │ AWS:${resiliencyvr_codebuild_lambda_role}     │                                                 │
│   │ loy-role-*                                    │        │ sts:AssumeRole                                │                                               │                                                 │
│   │ arn:aws:iam::${AWS::AccountId}:role/cdk-*-fil │        │                                               │                                               │                                                 │
│   │ e-publishing-*                                │        │                                               │                                               │                                                 │
│   │ arn:aws:iam::${AWS::AccountId}:role/cdk-readO │        │                                               │                                               │                                                 │
│   │ nlyRole                                       │        │                                               │                                               │                                                 │
├───┼───────────────────────────────────────────────┼────────┼───────────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ + │ arn:aws:lambda:${AWS::Region}:${AWS::AccountI │ Allow  │ lambda:CreateFunction                         │ AWS:${resiliencyvr_codebuild_lambda_role}     │                                                 │
│   │ d}:function:ExperimentLambdaFunction          │        │ lambda:DeleteFunction                         │                                               │                                                 │
│   │                                               │        │ lambda:GetCodeSigningConfig                   │                                               │                                                 │
│   │                                               │        │ lambda:GetFunction                            │                                               │                                                 │
│   │                                               │        │ lambda:GetFunctionCodeSigningConfig           │                                               │                                                 │
└───┴───────────────────────────────────────────────┴────────┴───────────────────────────────────────────────┴───────────────────────────────────────────────┴─────────────────────────────────────────────────┘
IAM Policy Changes
┌───┬───────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────┐
│   │ Resource                                                  │ Managed Policy ARN                                                                           │
├───┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
│ + │ ${Custom::S3AutoDeleteObjectsCustomResourceProvider/Role} │ {"Fn::Sub":"arn:${AWS::Partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"} │
└───┴───────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────┘
```
