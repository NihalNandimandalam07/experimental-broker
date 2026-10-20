# resource "aws_s3_bucket" "codepipeline_source_bucket" {
#   bucket = var.source_bucket_name
# }

# resource "aws_s3_bucket_public_access_block" "codepipeline_source_bucket" {
#   bucket                  = aws_s3_bucket.codepipeline_source_bucket.id
#   block_public_acls       = true
#   block_public_policy     = true
#   ignore_public_acls      = true
#   restrict_public_buckets = true
# }

resource "aws_s3_bucket" "codepipeline_artifact_bucket" {
  bucket = var.artifact_bucket_name
}

resource "aws_s3_bucket_public_access_block" "codepipeline_artifact_bucket" {
  bucket                  = aws_s3_bucket.codepipeline_artifact_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# resource "aws_s3_object" "source" {
#   bucket = aws_s3_bucket.codepipeline_source_bucket.bucket
#   key    = "build_temp/source.zip"
# }