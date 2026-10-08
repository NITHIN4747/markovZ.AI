module "secrets" {
  source = "./modules/secrets"

  environment = var.environment
  api_keys    = var.api_keys
}

module "app_host" {
  source = "./modules/app_host"

  environment   = var.environment
  instance_type = "t2.micro"
}
