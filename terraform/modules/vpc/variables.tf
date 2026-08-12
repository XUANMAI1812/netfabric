variable "region" {}
variable "vpc_cidr" {}
variable "public_subnet_cidr" {}
variable "private_subnet_cidr" {}
variable "availability_zone" {}
variable "name_prefix" {}

variable "peer_vpc_cidr" {}

variable "peer_public_ip" {
  type    = string
  default = null
}
