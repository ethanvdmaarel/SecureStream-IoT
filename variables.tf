variable "project_id" {
  description = "The GCP project ID created in the bootstrap step."
  type        = string
}

variable "region" {
  description = "Default region for all regional resources."
  type        = string
  default     = "asia-east1"
}
