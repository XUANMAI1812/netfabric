variable "public_subnet_id" {}
variable "security_group_id" {}
variable "name_prefix" {}

variable "iam_instance_profile_name" {
  type    = string
  default = null
}
