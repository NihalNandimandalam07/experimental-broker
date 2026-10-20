output "key_arn" {
  value       = aws_kms_key.kms_key.arn
  description = "The ARN of the KMS key."
  sensitive   = true
}