resource "aws_codebuild_project" "lambda_build_plan" {
  name          = var.build_plan_name
  description   = "Builds the lambda infra to run resiliency tests."
  build_timeout = "180"
  service_role  = aws_iam_role.codebuild_service.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"
  }

  logs_config {
    cloudwatch_logs {
      group_name  = var.codebuild_cloudwatch_log_group_name
      stream_name = var.codebuild_cloudwatch_log_stream_name
    }
  }

  source {
    type         = "CODEPIPELINE"
    insecure_ssl = false
    buildspec    = data.template_file.lambda_plan_buildspec.rendered
  }
}

resource "aws_codebuild_project" "lambda_build_apply" {
  name          = var.build_apply_name
  description   = "Builds the lambda infra to run resiliency tests."
  build_timeout = "180"
  service_role  = aws_iam_role.codebuild_service.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_MEDIUM"
    image        = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"
  }

  logs_config {
    cloudwatch_logs {
      group_name  = var.codebuild_cloudwatch_log_group_name
      stream_name = var.codebuild_cloudwatch_log_stream_name
    }
  }

  source {
    type         = "CODEPIPELINE"
    insecure_ssl = false
    buildspec    = data.template_file.lambda_apply_buildspec.rendered
  }
}

resource "aws_codebuild_project" "lambda_build_plan_destroy" {
  name          = var.build_plan_destroy_name
  description   = "Plans cleanup experiment broker lambda infra deployed through the pipeline."
  build_timeout = "180"
  service_role  = aws_iam_role.codebuild_service.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_MEDIUM"
    image        = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"
  }

  logs_config {
    cloudwatch_logs {
      group_name  = var.codebuild_cloudwatch_log_group_name
      stream_name = var.codebuild_cloudwatch_log_stream_name
    }
  }

  source {
    type         = "CODEPIPELINE"
    insecure_ssl = false
    buildspec    = data.template_file.lambda_plan_destroy_buildspec.rendered
  }
}

resource "aws_codebuild_project" "lambda_build_apply_destroy" {
  name          = var.build_apply_destroy_name
  description   = "Cleans up experiment broker lambda infra deployed through the pipeline."
  build_timeout = "180"
  service_role  = aws_iam_role.codebuild_service.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_MEDIUM"
    image        = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"
  }

  logs_config {
    cloudwatch_logs {
      group_name  = var.codebuild_cloudwatch_log_group_name
      stream_name = var.codebuild_cloudwatch_log_stream_name
    }
  }

  source {
    type         = "CODEPIPELINE"
    insecure_ssl = false
    buildspec    = data.template_file.lambda_apply_destroy_buildspec.rendered
  }
}