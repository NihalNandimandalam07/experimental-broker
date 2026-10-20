variable "environment_id" {
  description = "The environment experiment broker is deployed to."
  type        = string
}

variable "package_build_bucket_name" {
  description = "The name of the bucket to store lambda build packages."
  type        = string
}

variable "experiments_bucket_name" {
  description = "The name of the bucket to store experiment files."
  type        = string
}

variable "experiment_results_bucket_name" {
  description = "The name of the bucket to store experiment results."
  type        = string
}

variable "experiment_broker_deployment_type" {
  type        = string
  description = "The type of deployment, either 'ecs' or 'lambda'."
  validation {
    condition     = contains(["lambda", "ecs"], var.experiment_broker_deployment_type)
    error_message = "Invalid deployment type. Must be either 'lambda' or 'ecs'."
  }
}

variable "chaos_toolkit_type" {
  type        = string
  description = "The type of chaos toolkit to use, either 'main' or 'lite'."
  validation {
    condition     = contains(["main", "lite"], var.chaos_toolkit_type)
    error_message = "Invalid chaos toolkit type. Must be either 'main' or 'lite'."
  }
}

variable "sfn_lambda_name" {
  type        = string
  description = "The name of the lambda function for the experiment broker lambda deployment."
}

variable "sfn_lambda_log_level" {
  type        = string
  description = "The log level for the experiment broker lambda deployment."
}

variable "sfn_lambda_state_machine_name" {
  type        = string
  description = "The name of the state machine for the experiment broker lambda deployment."
}

variable "cloudwatch_log_group_name" {
  type        = string
  description = "The name of the cloudwatch log group."
}

variable "s3_key_alias" {
  type        = string
  description = "The alias for the s3 key."
}

variable "s3_key_description" {
  type        = string
  description = "The description for the s3 key."
}