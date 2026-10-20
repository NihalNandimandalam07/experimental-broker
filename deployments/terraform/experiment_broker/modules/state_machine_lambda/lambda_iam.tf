data "aws_iam_policy_document" "lambda_trust_policy" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy" "AWSLambdaBasicExecutionRole" {
  arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role" "experiment_lambda_role" {
  name               = "${var.lambda_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust_policy.json
}

data "aws_iam_policy_document" "experiment_lambda_policy_document" {
  statement {
    sid = "SSMPermissions"

    actions = [
      "ssm:SendCommand",
      "ssm:ListCommandInvocations",
    ]

    effect    = "Allow"
    resources = ["*"]
  }

  statement {
    sid = "S3Permissions"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]
    effect = "Allow"
    resources = [
      "${var.experiments_bucket_arn}",
      "${var.experiments_bucket_arn}/*",
      "${aws_s3_bucket.package_build_bucket.arn}",
      "${aws_s3_bucket.package_build_bucket.arn}/*"
    ]
  }

  statement {
    sid = "EC2Permissions"
    actions = [
      "ec2:DescribeInstances",
    ]
    effect    = "Allow"
    resources = ["*"]
  }

  statement {
    sid = "DynamoDBPermissions"

    actions = [
      "dynamodb:PutItem"
    ]

    effect    = "Allow"
    resources = ["*"]
  }

  statement {
    sid = "EC2ResourceLevelPermissions"
    actions = [
      "ec2:RunInstances",
      "ec2:TerminateInstances",
      "ec2:StopInstances",
      "ec2:StartInstances"
    ]

    effect    = "Allow"
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "ec2:ResourceTag/Type"
      values   = ["Resiliency"]
    }

  }

  statement {
    sid = "ECSPermissions"

    actions = [
      "ecs:List*",
      "ecs:Describe*",
      "ecs:StartTask",
      "ecs:RunTask",
      "ecs:StopTask",
      "ecs:ExecuteCommand",
      "ecs:DiscoverPollEndpoint",
      "ecs:PutAttributes",
      "ecs:UpdateTaskSet"
    ]

    effect    = "Allow"
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "ec2:ResourceTag/Type"
      values   = ["Resiliency"]
    }
  }
}

resource "aws_iam_policy" "experiment_lambda_policy" {
  name   = "experiment-lambda-policy"
  policy = data.aws_iam_policy_document.experiment_lambda_policy_document.json
}


resource "aws_iam_role_policy_attachment" "test-attach" {
  role       = aws_iam_role.experiment_lambda_role.name
  policy_arn = aws_iam_policy.experiment_lambda_policy.arn
}

resource "aws_iam_role_policy_attachment" "AWSLambdaBasicExecutionRole-attach" {
  role       = aws_iam_role.experiment_lambda_role.name
  policy_arn = data.aws_iam_policy.AWSLambdaBasicExecutionRole.arn
}

resource "aws_iam_role_policy_attachment" "demo-attach" {
  role       = aws_iam_role.experiment_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}