locals {
  experiments_bucket_name        = "${var.experiments_bucket_name}-${var.environment_id}"
  experiment_results_bucket_name = "${var.experiment_results_bucket_name}-${var.environment_id}"
  package_build_bucket_name      = "${var.package_build_bucket_name}-${var.environment_id}"
  sfn_lambda_name                = "${var.sfn_lambda_name}-${var.environment_id}"
  sfn_lambda_state_machine_name  = "${var.sfn_lambda_state_machine_name}-${var.experiment_broker_deployment_type}-${var.environment_id}"
}

module "s3_key" {
  source      = "./modules/kms_key"
  description = var.s3_key_description
  alias       = var.s3_key_alias
}

module "ssm_documents" {
  source = "./modules/ssm_documents"
}

module "experiments" {
  source                 = "./modules/s3_experiments_upload"
  experiment_bucket_name = local.experiments_bucket_name
}

module "state_machine" {
  count = var.experiment_broker_deployment_type == "lambda" ? 1 : 0

  source = "./modules/state_machine_lambda"

  environment_id            = var.environment_id
  lambda_log_level          = var.sfn_lambda_log_level
  lambda_name               = local.sfn_lambda_name
  experiment_results_bucket = local.experiment_results_bucket_name
  package_build_bucket      = local.package_build_bucket_name
  state_machine_name        = local.sfn_lambda_state_machine_name
  cloudwatch_log_group_name = var.cloudwatch_log_group_name
  s3_key_arn                = module.s3_key.key_arn
  experiments_bucket_arn    = module.experiments.bucket_arn
  chaos_toolkit_type        = var.chaos_toolkit_type
}

# module "state_machine" {
#   count = var.experiment-broker_deployment_type == "ecs" ? 1 : 0

#   source = "./modules/state_machine_ecs"
# }