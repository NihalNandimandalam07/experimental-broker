resource "aws_iam_role" "codepipeline_role" {
  name = "resiliencyvr-package-build-pipeline-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codepipeline.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "codepipeline_policy" {
  name = "codepipeline_policy"
  role = aws_iam_role.codepipeline_role.id

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect":"Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:GetBucketVersioning",
        "s3:PutObjectAcl",
        "s3:PutObject"
      ],
      "Resource": [
        "${aws_s3_bucket.codepipeline_bucket.arn}",
        "${aws_s3_bucket.codepipeline_bucket.arn}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "codestar-connections:UseConnection"
      ],
      "Resource": "${data.aws_codestarconnections_connection.mhiggins-github-connection.arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "codebuild:BatchGetBuilds",
        "codebuild:StartBuild"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role" "resiliencyvr_codebuild_package_role" {
  name = "resiliencyvr-codebuild-package-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "resiliencyvr_codebuild_package_policy_demo" {
  role = aws_iam_role.resiliencyvr_codebuild_package_role.name

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
        "*"
      ],
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
    },
    { "Effect": "Allow",
      "Action": [
          "codeartifact:GetAuthorizationToken",
          "codeartifact:GetRepositoryEndpoint"
      ],
      "Resource": [
          "${aws_codeartifact_repository.vr_ca_dev.arn}",
          "${aws_codeartifact_domain.vr_ca_dev_domain.arn}/*",
          "${aws_codeartifact_domain.vr_ca_dev_domain.arn}"

      ]
    },
    { "Effect": "Allow",
      "Action": "sts:GetServiceBearerToken",
      "Resource": "*",
      "Condition": {
          "StringEquals": {
              "sts:AWSServiceName": "codeartifact.amazonaws.com"
            }
        }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": [
        "${aws_s3_bucket.codepipeline_bucket.arn}",
        "${aws_s3_bucket.codepipeline_bucket.arn}/*"
      ]
    }
  ]
}
POLICY
}



resource "aws_iam_role" "resiliencyvr_codebuild_lambda_role" {
  name = "resiliencyvr-codebuild-lambda-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "resiliencyvr_codebuild_lambda_policy_demo" {
  role = aws_iam_role.resiliencyvr_codebuild_lambda_role.name

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
        "*"
      ],
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
    },
    {
      "Effect": "Allow",
      "Resource": [
        "*"
      ],
      "Action": [
        "ssm:CreateDocument",
        "ssm:AddTagsToResource",
        "ssm:DescribeDocument",
        "ssm:GetDocument",
        "ssm:DescribeDocumentPermission",
        "ssm:DeleteDocument"
      ]
    },
    { "Effect": "Allow",
      "Action": [
          "codeartifact:GetAuthorizationToken",
          "codeartifact:GetRepositoryEndpoint"
      ],
      "Resource": [
          "${aws_codeartifact_repository.vr_ca_dev.arn}",
          "${aws_codeartifact_domain.vr_ca_dev_domain.arn}/*",
          "${aws_codeartifact_domain.vr_ca_dev_domain.arn}"

      ]
    },
    { "Effect": "Allow",
      "Action": "sts:GetServiceBearerToken",
      "Resource": "*",
      "Condition": {
          "StringEquals": {
              "sts:AWSServiceName": "codeartifact.amazonaws.com"
            }
        }
    },
    { "Effect": "Allow",
      "Action": "sts:GetServiceBearerToken",
      "Resource": "*",
      "Condition": {
          "StringEquals": {
              "sts:AWSServiceName": "codebuild.amazonaws.com"
            }
        }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:GetObject",
        "s3:GetObjectTagging",
        "s3:GetObjectVersion",
        "s3:GetBucketVersioning",
        "s3:GetAccelerateConfiguration",
        "s3:PutObjectAcl",
        "s3:PutObject",
        "s3:PutObjectTagging",
        "s3:PutBucketTagging",
        "s3:PutBucketVersioning",
        "s3:PutBucketAcl",
        "s3:PutBucketPolicy",
        "s3:PutBucketEncryption",
        "s3:PutEncryptionConfiguration",
        "s3:PutBucketPublicAccessBlock",
        "s3:ListBucket",
        "s3:DeleteBucket",
        "s3:Get*"
      ],
      "Resource": [
        "${aws_s3_bucket.codepipeline_bucket.arn}",
        "${aws_s3_bucket.codepipeline_bucket.arn}/*",
        "arn:aws:s3:::${var.backend_bucket_name}",
        "arn:aws:s3:::${var.backend_bucket_name}/*",
        "arn:aws:s3:::${var.experiments_bucket_name}",
        "arn:aws:s3:::${var.experiments_bucket_name}/*",
        "arn:aws:s3:::${var.experiment_package_bucket}",
        "arn:aws:s3:::${var.experiment_package_bucket}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:DescribeKey",
        "kms:GetKeyPolicy",
        "kms:GetKeyRotationStatus",
        "kms:ListResourceTags",
        "kms:GenerateDataKey",
        "kms:Decrypt",
        "kms:TagResource",
        "kms:CreateKey",
        "kms:EnableKeyRotation",
        "kms:ScheduleKeyDeletion"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:GetRole",
        "iam:GetPolicy",
        "iam:ListRolePolicies",
        "iam:GetPolicyVersion",
        "iam:ListAttachedRolePolicies",
        "iam:CreateRole",
        "iam:CreatePolicy",
        "iam:TagPolicy",
        "iam:TagRole",
        "iam:PassRole",
        "iam:AttachRolePolicy",
        "iam:ListPolicyVersions",
        "iam:CreatePolicyVersion"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:ListAliases",
        "lambda:ListCodeSigningConfigs",
        "lambda:ListEventSourceMappings",
        "lambda:ListFunctionEventInvokeConfigs",
        "lambda:ListFunctions",
        "lambda:ListFunctionsByCodeSigningConfig",
        "lambda:ListFunctionUrlConfigs",
        "lambda:ListLayers",
        "lambda:ListLayerVersions",
        "lambda:ListProvisionedConcurrencyConfigs",
        "lambda:ListTags"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:GetFunction",
        "lambda:GetFunctionCodeSigningConfig",
        "lambda:GetCodeSigningConfig",
        "lambda:DeleteFunction",
        "lambda:ListVersionsByFunction",
        "lambda:UpdateFunctionCode",
        "lambda:TagResource"
      ],
      "Resource": "arn:aws:lambda:*:*:function:${var.experiment_lambda_name}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/${var.backend_table_name}"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "states:CreateStateMachine",
        "states:TagResource",
        "states:DescribeStateMachine",
        "states:ListTagsForResource",
        "states:DeleteStateMachine",
        "states:UpdateStateMachine"
      ],
      "Resource": ["arn:aws:states:*:*:stateMachine:${var.statemachine_name}"]
    }
  ]
}
POLICY
}
