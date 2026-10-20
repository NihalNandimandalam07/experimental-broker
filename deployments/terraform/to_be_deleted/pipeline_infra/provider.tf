terraform {
  backend "s3" {
    dynamodb_table = "experiment_pipeline_terraform_state_demo"
    bucket         = "experiment-pipeline-backend-bucket-demo"
    region         = "us-east-1"
    key            = "pipeline_infra.terraform.tfstate"
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      Team = "ResiliencyTeam",
    }
  }
}