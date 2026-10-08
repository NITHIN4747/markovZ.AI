variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment name (e.g., dev, prod)"
}

variable "api_keys" {
  type = map(string)
  default = {
    gemini   = "mock-gemini-key"
    groq     = "mock-groq-key"
    deepseek = "mock-deepseek-key"
  }
  description = "Map of API keys to store in SSM"
}
