resource "aws_iam_role" "codepipeline_role" {
  name = "experiment-broker-lambda-build-pipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "codepipeline.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

data "aws_iam_policy_document" "codepipeline" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetBucketVersioning",
      "s3:PutObjectAcl",
      "s3:PutObject"
    ]

    resources = [
      aws_s3_bucket.codepipeline_artifact_bucket.arn,
      "${aws_s3_bucket.codepipeline_artifact_bucket.arn}/*"
    ]
  }

  statement {
    actions = [
      "codestar-connections:UseConnection"
    ]

    resources = [
      resource.aws_codestarconnections_connection.connection.arn
    ]
  }

  statement {
    actions = [
      "codebuild:BatchGetBuilds",
      "codebuild:StartBuild"
    ]

    resources = [
      aws_codebuild_project.lambda_build_plan.arn,
      aws_codebuild_project.lambda_build_apply.arn,
      aws_codebuild_project.lambda_build_plan_destroy.arn,
      aws_codebuild_project.lambda_build_apply_destroy.arn
    ]
  }
}

resource "aws_iam_role_policy" "codepipeline_policy" {
  name = "codepipeline_policy"
  role = aws_iam_role.codepipeline_role.id

  policy = data.aws_iam_policy_document.codepipeline.json
}

resource "aws_iam_role" "codebuild_service" {
  name = "experiment-broker-codebuild-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "codebuild.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "codebuild_service" {
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
  role       = aws_iam_role.codebuild_service.name
}

# data "aws_iam_policy_document" "codebuild_service" {
# statement {
#   actions = [
#     "logs:CreateLogGroup",
#     "logs:CreateLogStream",
#     "logs:PutLogEvents",
#     "logs:GetLogEvents"
#   ]

#   resources = [
#     aws_cloudwatch_log_group.experiment_broker.arn,
#     "${aws_cloudwatch_log_group.experiment_broker.arn}:*"
#   ]
# }

# statement {
#   actions = [
#     "s3:GetObject",
#     "s3:GetObjectVersion",
#     "s3:GetBucketVersioning",
#     "s3:PutObjectAcl",
#     "s3:PutObject"
#   ]

#   resources = [
#     aws_s3_bucket.codepipeline_artifact_bucket.arn,
#     "${aws_s3_bucket.codepipeline_artifact_bucket.arn}/*",
#   ]
# }
# statement {
#   actions = [
#     "s3:PutObject",
#     "s3:ListBucket",
#     "s3:Get*",
#     "s3:Create*"
#   ]

#   resources = [
#     "arn:aws:s3:::${var.backend_bucket}",
#     "arn:aws:s3:::${var.backend_bucket}/*",
#     "arn:aws:s3:::${var.experiment_package_bucket}",
#     "arn:aws:s3:::${var.experiment_package_bucket}/*",
#     "arn:aws:s3:::resiliencyvr-package-build-bucket-demo",
#     "arn:aws:s3:::resiliencyvr-package-build-bucket-demo/*"
#   ]
# }

# statement {
#   actions = [
#     "dynamodb:PutItem",
#     "dynamodb:GetItem",
#     "dynamodb:DeleteItem"
#   ]

#   resources = [
#     "arn:aws:dynamodb:*:*:table/${var.backend_table_name}",
#     "arn:aws:dynamodb:*:*:table/${var.backend_table_name}/*"
#   ]
# }

# statement {
#   actions = [
#     "iam:GetPolicy",
#     "iam:GetPolicyVersion"
#   ]

#   resources = [
#     "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
#   ]
# }

# statement {
#   actions = [
#     "iam:Get*",
#     "iam:List*"
#   ]

#   resources = ["*"]
# }

# statement {
#   actions = [
#     "iam:DeleteRole",
#     "iam:CreatePolicy",
#     "iam:CreateRole",
#     "iam:TagRole",
#     "iam:AttachRolePolicy",
#   ]

#   resources = [
#     "arn:aws:iam::*:role/experiment_lambda_role",
#     "arn:aws:iam::*:role/step-function-role"
#     ]
# }

# statement {
#   actions = [
#     "ssm:CreateDocument",
#     "ssm:AddTagsToResource",
#     "ssm:Describe*",
#     "ssm:Get*",
#     "ssm:DeleteDocument",
#   ]

#   resources = ["*"]
# }

# statement {
#   actions = [
#     "s3:DeleteBucket",
#   ]

#   resources = ["arn:aws:s3:::resiliencyvr-package-build-bucket-demo"]
# }

# statement {
#   actions = [
#     "kms:CreateKey",
#     "kms:DescribeKey",
#     "kms:EnableKey",
#     "kms:TagResource",
#     "kms:Get*",
#     "kms:List*",
#     "kms:ScheduleKeyDeletion",
#   ]

#   resources = [
#     "*"
#   ]
# }
# }

# resource "aws_iam_role_policy" "codebuild_service" {
#   role = aws_iam_role.codebuild_service.name

#   policy = data.aws_iam_policy_document.codebuild_service.json
# }