variable "environment" {
  type        = string
  description = "Environment name (e.g., dev, prod)"
}

variable "instance_type" {
  type        = string
  default     = "t2.micro"
  description = "EC2 instance type"
}
