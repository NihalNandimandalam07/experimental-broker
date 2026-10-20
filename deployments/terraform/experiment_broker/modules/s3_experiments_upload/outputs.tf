output "bucket_name" {
  value       = aws_s3_bucket.experiments_bucket.bucket
  description = "The name of the S3 bucket."
  sensitive   = true
}

output "bucket_arn" {
  value       = aws_s3_bucket.experiments_bucket.arn
  description = "The ARN of the S3 bucket."
  sensitive   = true
}