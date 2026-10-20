variable "environment_id" {
  type        = string
  description = "Unique ID for separating environments."
}

variable "lambda_log_level" {
  type        = string
  description = "Log level for the Lambda Python runtime."
}

variable "lambda_name" {
  type        = string
  description = "name to use for lambda."
}

variable "experiment_results_bucket" {
  type        = string
  description = "Name of the experiment results bucket."
}

variable "package_build_bucket" {
  type        = string
  description = "Bucket to place the lambda package in."
}

variable "state_machine_name" {
  type        = string
  description = "Name of the state machine."
}

variable "cloudwatch_log_group_name" {
  type        = string
  description = "The name of the cloudwatch log group."
}

variable "s3_key_arn" {
  type        = string
  description = "The ARN of the KMS key to encrypt the S3 bucket."
}

variable "experiments_bucket_arn" {
  type        = string
  description = "ARN of the experiments bucket."
}

variable "chaos_toolkit_type" {
  type        = string
  description = "The type of chaos toolkit to use, either 'main' or 'lite'."

  validation {
    condition     = contains(["main", "lite"], var.chaos_toolkit_type)
    error_message = "Invalid chaos toolkit type. Must be either 'main' or 'lite'."
  }
}