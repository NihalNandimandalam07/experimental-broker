resource "aws_cloudwatch_log_group" "state_machine_logs" {
  name = var.cloudwatch_log_group_name
}