locals {
  module_path = "deployments/terraform/experiment_broker"
}

data "template_file" "lambda_plan_buildspec" {
  template = file("${path.module}/buildspecs/buildspec-lambda.yaml")

  vars = {
    TF_VERSION       = var.terraform_version
    TF_COMMAND       = <<EOF
plan -out=tfplan.plan \
        -var "environment_id=${var.environment_id}" \
        -var "experiment_results_bucket_name=${var.experiment_results_bucket_name}" \
        -var "package_build_bucket_name=${var.package_build_bucket_name}" \
        -var "experiments_bucket_name=${var.experiments_bucket_name}" \
        -var "experiment_broker_deployment_type=${var.experiment_broker_deployment_type}" \
        -var "sfn_lambda_name=${var.sfn_lambda_name}" \
        -var "sfn_lambda_log_level=${var.sfn_lambda_log_level}" \
        -var "sfn_lambda_state_machine_name=${var.sfn_lambda_state_machine_name}" \
        -var "cloudwatch_log_group_name=${var.sfn_cloudwatch_log_group_name}" \
        -var "s3_key_alias=${var.s3_key_alias}" \
        -var "s3_key_description=${var.s3_key_description}" \
        -var "chaos_toolkit_type=${var.chaos_toolkit_type}"
EOF
    TF_MODULE_PATH   = local.module_path
    OUTPUT_ARTIFACTS = "tfplan.plan"
  }
}

data "template_file" "lambda_apply_buildspec" {
  template = file("${path.module}/buildspecs/buildspec-lambda.yaml")

  vars = {
    TF_VERSION       = var.terraform_version
    TF_COMMAND       = <<EOF
apply -auto-approve \
        -var "environment_id=${var.environment_id}" \
        -var "experiment_results_bucket_name=${var.experiment_results_bucket_name}" \
        -var "package_build_bucket_name=${var.package_build_bucket_name}" \
        -var "experiments_bucket_name=${var.experiments_bucket_name}" \
        -var "experiment_broker_deployment_type=${var.experiment_broker_deployment_type}" \
        -var "sfn_lambda_name=${var.sfn_lambda_name}" \
        -var "sfn_lambda_log_level=${var.sfn_lambda_log_level}" \
        -var "sfn_lambda_state_machine_name=${var.sfn_lambda_state_machine_name}" \
        -var "cloudwatch_log_group_name=${var.sfn_cloudwatch_log_group_name}" \
        -var "s3_key_alias=${var.s3_key_alias}" \
        -var "s3_key_description=${var.s3_key_description}" \
        -var "chaos_toolkit_type=${var.chaos_toolkit_type}" \
        "$${CODEBUILD_SRC_DIR_build_output}/${local.module_path}/tfplan.plan"
      EOF
    TF_MODULE_PATH   = local.module_path
    OUTPUT_ARTIFACTS = ""
  }
}

data "template_file" "lambda_plan_destroy_buildspec" {
  template = file("${path.module}/buildspecs/buildspec-lambda.yaml")

  vars = {
    TF_VERSION       = var.terraform_version
    TF_COMMAND       = <<EOF
plan -destroy -out=tfplan.plan \
        -var "environment_id=${var.environment_id}" \
        -var "experiment_results_bucket_name=${var.experiment_results_bucket_name}" \
        -var "package_build_bucket_name=${var.package_build_bucket_name}" \
        -var "experiments_bucket_name=${var.experiments_bucket_name}" \
        -var "experiment_broker_deployment_type=${var.experiment_broker_deployment_type}" \
        -var "sfn_lambda_name=${var.sfn_lambda_name}" \
        -var "sfn_lambda_log_level=${var.sfn_lambda_log_level}" \
        -var "sfn_lambda_state_machine_name=${var.sfn_lambda_state_machine_name}" \
        -var "cloudwatch_log_group_name=${var.sfn_cloudwatch_log_group_name}" \
        -var "s3_key_alias=${var.s3_key_alias}" \
        -var "s3_key_description=${var.s3_key_description}" \
        -var "chaos_toolkit_type=${var.chaos_toolkit_type}"
EOF
    TF_MODULE_PATH   = local.module_path
    OUTPUT_ARTIFACTS = "tfplan.plan"
  }
}

data "template_file" "lambda_apply_destroy_buildspec" {
  template = file("${path.module}/buildspecs/buildspec-lambda.yaml")

  vars = {
    TF_VERSION       = var.terraform_version
    TF_COMMAND       = <<EOF
apply -destroy -auto-approve \
        -var "environment_id=${var.environment_id}" \
        -var "experiment_results_bucket_name=${var.experiment_results_bucket_name}" \
        -var "package_build_bucket_name=${var.package_build_bucket_name}" \
        -var "experiments_bucket_name=${var.experiments_bucket_name}" \
        -var "experiment_broker_deployment_type=${var.experiment_broker_deployment_type}" \
        -var "sfn_lambda_name=${var.sfn_lambda_name}" \
        -var "sfn_lambda_log_level=${var.sfn_lambda_log_level}" \
        -var "sfn_lambda_state_machine_name=${var.sfn_lambda_state_machine_name}" \
        -var "cloudwatch_log_group_name=${var.sfn_cloudwatch_log_group_name}" \
        -var "s3_key_alias=${var.s3_key_alias}" \
        -var "s3_key_description=${var.s3_key_description}" \
        -var "chaos_toolkit_type=${var.chaos_toolkit_type}" \
        "$${CODEBUILD_SRC_DIR_build_output}/${local.module_path}/tfplan.plan"
EOF
    TF_MODULE_PATH   = local.module_path
    OUTPUT_ARTIFACTS = ""
  }
}
