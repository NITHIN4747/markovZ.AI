resource "aws_ssm_parameter" "secrets" {
  for_each = var.api_keys

  name  = "/market-ai/${var.environment}/${each.key}-api-key"
  type  = "SecureString"
  value = each.value
}
