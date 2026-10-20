resource "aws_s3_bucket" "experiments_bucket" {
  bucket = var.experiment_bucket_name
}

resource "aws_s3_bucket_public_access_block" "experiments_bucket_acl" {
  bucket                  = aws_s3_bucket.experiments_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "experiments_bucket_versioning" {
  bucket = aws_s3_bucket.experiments_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "experiments_bucket_sse" {
  bucket = aws_s3_bucket.experiments_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_object" "experiment_files" {
  for_each     = fileset("${path.module}/experiments/", "**")
  bucket       = aws_s3_bucket.experiments_bucket.id
  key          = each.value
  source       = "${path.module}/experiments/${each.value}"
  etag         = filemd5("${path.module}/experiments/${each.value}")
  content_type = "application/x-yaml"
}