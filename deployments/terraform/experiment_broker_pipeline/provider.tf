terraform {
  backend "s3" {
    dynamodb_table = "experiment-broker-terraform-state-default"
    bucket         = "experiment-broker-backend-bucket-default"
    region         = "us-east-1"
    key            = "experiment_broker_pipeline.terraform.tfstate"
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