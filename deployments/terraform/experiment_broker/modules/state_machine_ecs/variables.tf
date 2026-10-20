variable "lambda_relative_path" {
  description = "Used in the Lambda build"
  type        = string
  default     = "./../../Experiment-Broker-Module/experiment_code/"
}

variable "lambda_log_level" {
  description = "Log level for the Lambda Python runtime."
  type        = string
  default     = "ERROR"
}

variable "lambda_name" {
  description = "name to use for lambda"
  type        = string
  default     = "experiment_lambda"
}

variable "owner" {
  description = "Name of the team member who owns the resource. Used so multiple lambdas can be deployed"
  type        = string
  default     = "Resiliency_Team"
}

variable "experiment_bucket" {
  description = "Bucket to place the lambda package in"
  type        = string
  default     = "experiment-broker-package-build-bucket"
}

variable "environment_id" {
  type        = string
  default     = "demo"
  description = "Unique ID for separating environments"
}

variable "iam_tag_key" {
  type        = string
  default     = "Team"
  description = "Tag key name"
}

variable "iam_tag_value" {
  type        = string
  default     = "Team"
  description = "Tag key value"
}

variable "ecs_route_table_ids" {
  description = "Route table ids to assocuiate with the S3 Gateway Endpoint"
  type        = list(string)
}

variable "ecs_subnet_ids" {
  description = "Subnet Ids to launch the ECS Fargate cluster in"
  type        = list(string)
}

variable "ecs_vpc_id" {
  description = "VPC launch the ECS Fargate cluster in"
  type        = string
}

variable "state_machine_name" {
  type        = string
  description = "Name of the state machine"
}

variable "sfn_parallel_max_concurrency" {
  type        = number
  description = "Max concurrency for parallel step function runs"
}