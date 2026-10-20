data "aws_codestarconnections_connection" "mhiggins-github-connection" {
  arn = var.codestar_connection_arn
}

data "template_file" "resiliencyvr_package_buildspec" {
  template = file("${path.module}/buildspec-resiliencyvr.yml")
  vars = {
    DOMAIN_NAME = var.domain_name
    OWNER       = var.owner
    REPO_NAME   = var.repo_name
    SECRET_ID   = "github/personal/mhiggins"
  }
}

data "template_file" "lambda_buildspec" {
  template = file("${path.module}/buildspec-lambda.yml")
  vars = {
    DOMAIN_NAME = var.domain_name
    OWNER       = var.owner
    REPO_NAME   = var.repo_name
    SECRET_ID   = "github/personal/mhiggins"
  }
}