terraform {
  backend "s3" {
    dynamodb_table = "experiment-broker-backend-table-nn"
    bucket         = "experiment-broker-backend-nn"
    region         = "us-east-2"
    key            = "experiment_broker.terraform.tfstate"
  }
}

provider "aws" {
  region = "us-east-2"
}