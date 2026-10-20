locals {
  state_machine_name = "${var.state_machine_name}-${var.environment_id}"
}

data "aws_iam_policy_document" "step_function_assume_role_policy_document" {
  version = "2012-10-17"
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "step_function_policy_document" {
  version = "2012-10-17"
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [resource.aws_lambda_function.experiment_lambda.arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "events:PutTargets",
      "events:PutRule",
      "events:DescribeRule"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecr:*",
      "ecs:*"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = [aws_iam_role.experiment_ecs_role.arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution",
      "states:DescribeExecution",
      "states:StopExecution"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "cloudwatch:PutMetricData",
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "step_function_role" {
  name               = "experiment-broker-step-function-${data.aws_region.current.name}-role"
  assume_role_policy = data.aws_iam_policy_document.step_function_assume_role_policy_document.json
}

resource "aws_iam_policy" "step_function_policy" {
  name   = "experiment-broker-step-function-${data.aws_region.current.name}-policy"
  policy = data.aws_iam_policy_document.step_function_policy_document.json
}

resource "aws_iam_document_attachment" "step_function_policy_attachment" {
  policy_arn = aws_iam_policy.step_function_policy.arn
  role       = aws_iam_role.step_function_role.name
}

resource "aws_cloudwatch_log_group" "state_machine_logs" {
  name = "/aws/stepfunction/Experiment_Broker"
}


resource "aws_sfn_state_machine" "state_machine" {
  name     = local.state_machine_name
  role_arn = aws_iam_role.step_function_role.arn

  tracing_configuration {
    enabled = true
  }

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.state_machine_logs.arn}:*"
    level                  = "ALL"
    include_execution_data = true
  }

  type = "STANDARD"

  definition = templatefile("${path.module}/state_machine_ecs.json", { ecs_subnet_ids = var.ecs_subnet_ids, cluster_name = aws_ecs_cluster.ecs_cluster.name, task_def_arn = aws_ecs_task_definition.payload_processor_task.arn, parallel_max_concurrency = var.sfn_parallel_max_concurrency })
}