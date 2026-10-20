variable "environment_id" {
  description = "The environment experiment broker is deployed to."
  type        = string
}

variable "provider_region" {
  description = "The region to deploy the experiment broker to."
  type        = string
}

variable "backend_table_name" {
  description = "The name of the dynamodb table to store terraform state."
  type        = string
}

variable "backend_table_key" {
  description = "The key of the dynamodb table to store terraform state."
  type        = string
}

variable "backend_bucket_name" {
  description = "The name of the bucket to store terraform state."
  type        = string
}
