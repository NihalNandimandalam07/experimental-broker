resource "aws_kms_key" "kms_key" {
  description             = var.description
  deletion_window_in_days = 14
  enable_key_rotation     = true
}

resource "aws_kms_alias" "kms_alias" {
  name          = var.alias
  target_key_id = aws_kms_key.kms_key.key_id
}