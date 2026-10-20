variable "codestar_connection_arn" {
  type        = string
  description = "ARN for the existing Codestar Connection"
  default     = "arn:aws:codestar-connections:us-east-1:899456967600:connection/54897a30-26c4-44fa-ab2c-41b88d4fae31" //mhiggins-vr account
  #  default = "arn:aws:codestar-connections:us-east-1:899456967600:connection/7af0117b-b256-4256-828b-592f7828d4fa"
}

variable "repository_id" {
  type        = string
  description = "Repository Path in Github"
  default     = "mhiggins-vr/Experiment-pipeline"
}

variable "repository_branch" {
  type        = string
  description = "Repository branch of the resiliency code"
  default     = "master"
}

variable "domain_name" {
  type        = string
  description = "Domain for the CodeArtifact repository"
  default     = "twitch-ca-twitch"
}

variable "repo_name" {
  type        = string
  description = "Name of the CodeArtifact repository"
  default     = "twitch-ca-twitch"
}

variable "owner" {
  type        = string
  description = "Owner of the CodeArtifact repository"
  default     = "899456967600"
}

variable "experiments_bucket_name" {
  type        = string
  description = "Name of the experiments bucket"
  default     = "resiliency-testing-experiments-alpha"
}

variable "experiment_package_bucket" {
  description = "Bucket to place the lambda package in"
  type        = string
  default     = "resiliencyvr-package-build-bucket-demo"
}

variable "backend_bucket_name" {
  type        = string
  description = "Name of the backend bucket"
  default     = "experiment-pipeline-backend-bucket-alpha"
}

variable "backend_table_name" {
  type        = string
  description = "Name of the backend Dynamodb table"
  default     = "experiment_pipeline_terraform_state_alpha"
}

variable "statemachine_name" {
  type        = string
  description = "Name of the state machine"
  default     = "Experiment_broker"
}

variable "experiment_lambda_name" {
  type        = string
  description = "Name of the experiment lambda function"
  default     = "experiment_lambda-Resiliency_Team"
}

variable "github_secret_arn" {
  type        = string
  description = "Arn for the github secret token"
  default     = "arn:aws:secretsmanager:us-east-1:899456967600:secret:github/personal/mhiggins-ulZMpw"
}