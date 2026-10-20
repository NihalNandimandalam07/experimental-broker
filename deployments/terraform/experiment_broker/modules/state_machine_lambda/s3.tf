data "local_file" "lambda_zip" {
  filename   = "${path.root}/build_temp/experiment_broker_lambda.zip"
  depends_on = [null_resource.build_lambda_package]
}

resource "null_resource" "build_lambda_package" {
  provisioner "local-exec" {
    command = "chmod +x ${path.module}/build.sh && ${path.module}/build.sh"

    environment = {
      CHAOS_TOOLKIT_TYPE = var.chaos_toolkit_type
    }
  }

  triggers = {
    deployment = timestamp()
  }
}

resource "aws_s3_object" "lambda_file" {
  bucket     = var.package_build_bucket
  key        = "experiment-broker-lambda-build-${var.environment_id}-${timestamp()}.zip"
  source     = data.local_file.lambda_zip.filename
  depends_on = [null_resource.build_lambda_package]
  kms_key_id = var.s3_key_arn
}

resource "aws_s3_bucket" "package_build_bucket" {
  bucket = var.package_build_bucket
}

resource "aws_s3_bucket_public_access_block" "package_build_bucket" {
  bucket                  = aws_s3_bucket.package_build_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "experiment_results_bucket" {
  bucket = var.experiment_results_bucket
}

resource "aws_s3_bucket_public_access_block" "experiment_results_bucket" {
  bucket                  = aws_s3_bucket.experiment_results_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

