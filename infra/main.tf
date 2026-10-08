module "secrets" {
  source = "./modules/secrets"

  environment = var.environment
  api_keys    = var.api_keys
}
