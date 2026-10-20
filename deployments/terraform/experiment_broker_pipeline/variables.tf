variable "environment_id" {
  type        = string
  description = "The environment experiment broker is deployed to."
}

variable "repository_id" {
  type        = string
  description = "Repository Path in Github"
}

variable "repository_branch" {
  type        = string
  description = "Repository branch of the resiliency code"
}

variable "ecr_repository_name" {
  type        = string
  description = "The name of the ECR repository to store the experiment broker image."
}

variable "experiments_bucket_name" {
  type        = string
  description = "The name of the bucket to store experiment files."
}

variable "experiment_results_bucket_name" {
  type        = string
  description = "The name of the bucket to store experiment results."
}

variable "package_build_bucket_name" {
  type        = string
  description = "The name of the bucket to store lambda build packages."
}

variable "build_pipeline_name" {
  type        = string
  description = "The name of the pipeline that deploys experiment broker infrastructure."
}

variable "destroy_pipeline_name" {
  type        = string
  description = "The name of the pipeline that cleans up the experiment broker deployment."
}

variable "terraform_version" {
  type        = string
  description = "The version of terraform to use."
}

variable "artifact_bucket_name" {
  type        = string
  description = "The name of the bucket to store codepipeline artifacts."
}

variable "codestar_connection_name" {
  type        = string
  description = "The name of the connection to be created. The name must be unique in the calling AWS account. Changing this name will create a new resource."
}

variable "build_plan_name" {
  type        = string
  description = "The name of the terraform plan codebuild project."
}

variable "build_apply_name" {
  type        = string
  description = "The name of the terraform apply codebuild project."
}

variable "build_plan_destroy_name" {
  type        = string
  description = "The name of the terraform destroy codebuild project that cleans up the deployment through codepipeline."
}

variable "build_apply_destroy_name" {
  type        = string
  description = "The name of the terraform destroy codebuild project that plans cleanup of deployment through codepipeline."
}

variable "codebuild_cloudwatch_log_group_name" {
  type        = string
  description = "The name of the cloudwatch log group for the pipeline codebuilds."
}

variable "codebuild_cloudwatch_log_stream_name" {
  type        = string
  description = "The name of the cloudwatch log stream."
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

variable "sfn_cloudwatch_log_group_name" {
  type        = string
  description = "The name of the cloudwatch log group for the experiment broker state machine."
}

variable "s3_key_alias" {
  type        = string
  description = "The alias for the s3 key."
}

variable "s3_key_description" {
  type        = string
  description = "The description for the s3 key."
}

variable "experiment_broker_deployment_type" {
  type        = string
  description = "The type of deployment, either ECS or lambda."
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

variable "pipeline_build_docker_image_name" {
  type = string
  description = "The name of the docker image to use for the pipeline build, including tags or SHA256 repo digests."
}