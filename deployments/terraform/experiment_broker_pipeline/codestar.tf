resource "aws_codestarconnections_connection" "connection" {
  provider_type = "GitHub"
  name          = var.codestar_connection_name
}
