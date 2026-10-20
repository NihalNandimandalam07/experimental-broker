locals {
  lambda_src_path      = "${path.module}./../../Experiment-Broker-Module/experiment_code/lambda"
}

resource "aws_lambda_function" "experiment_lambda" {
  function_name = var.lambda_name
  description   = "Experiment Broker Lambda Function"
  role          = aws_iam_role.experiment_lambda_role.arn
  runtime       = "python3.11"
  handler       = "handler.handler"
  memory_size   = 1024
  timeout       = 600

  s3_bucket = var.package_build_bucket
  s3_key    = aws_s3_object.lambda_file.id

  source_code_hash = data.local_file.lambda_zip.content_md5
  environment {
    variables = {
      LOG_LEVEL          = var.lambda_log_level
      CHAOS_TOOLKIT_TYPE = var.chaos_toolkit_type
    }
  }
  lifecycle {
    ignore_changes = [environment]
  }

  depends_on = [aws_s3_object.lambda_file]
}

