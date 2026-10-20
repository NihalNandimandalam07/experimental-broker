resource "aws_cloudwatch_log_group" "experiment_broker" {
  name              = var.codebuild_cloudwatch_log_group_name
  retention_in_days = 30
}