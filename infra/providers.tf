variable "use_floci" {
  type    = bool
  default = true
  description = "If true, route all AWS API calls to the local Floci emulator."
}

variable "region" {
  type    = string
  default = "ap-south-1"
}

provider "aws" {
  region                      = var.region
  access_key                  = var.use_floci ? "test" : null
  secret_key                  = var.use_floci ? "test" : null
  skip_credentials_validation = var.use_floci
  skip_metadata_api_check     = var.use_floci
  skip_requesting_account_id  = var.use_floci
  s3_use_path_style           = var.use_floci

  dynamic "endpoints" {
    for_each = var.use_floci ? [1] : []
    content {
      s3  = "http://localhost:4566"
      ssm = "http://localhost:4566"
      ec2 = "http://localhost:4566"
      iam = "http://localhost:4566"
      sts = "http://localhost:4566"
    }
  }
}
