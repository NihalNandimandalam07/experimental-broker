resource "aws_s3_bucket" "codepipeline_bucket" {
  bucket = "resiliencyvr-package-build-bucket-demo"
}

#resource "aws_s3_bucket_acl" "codepipeline_bucket_acl" {
#  bucket = aws_s3_bucket.codepipeline_bucket.id
#  acl    = "private"
#}

resource "aws_s3_bucket_public_access_block" "codepipeline_bucket" {
  bucket                  = aws_s3_bucket.codepipeline_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
