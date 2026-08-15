terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region  = "ap-southeast-1"
  profile = "netfabric"
}

module "vpc" {
  source               = "../../modules/vpc"
  region               = "ap-southeast-1"
  vpc_cidr             = "10.0.0.0/16"
  public_subnet_cidr   = "10.0.1.0/24"
  private_subnet_cidr  = "10.0.2.0/24"
  availability_zone    = "ap-southeast-1a"
  name_prefix          = "hub"
  peer_vpc_cidr        = "10.1.0.0/16"
  peer_public_ip  = var.peer_public_ip
}

module "nat_instance" {
  source             = "../../modules/nat-instance"
  public_subnet_id   = module.vpc.public_subnet_id
  security_group_id  = module.vpc.nat_bastion_sg_id
  name_prefix        = "hub"
  iam_instance_profile_name  = module.iam.instance_profile_name
}

resource "aws_route" "private_to_nat" {
  route_table_id         = module.vpc.private_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  network_interface_id   = module.nat_instance.primary_network_interface_id
}

module "iam" {
  source      = "../../modules/iam"
  name_prefix = "hub"
}

module "test_host" {
  source                     = "../../modules/test-host"
  vpc_id                     = module.vpc.vpc_id
  private_subnet_id          = module.vpc.private_subnet_id
  peer_vpc_cidr              = "10.1.0.0/16"
  iam_instance_profile_name  = module.iam.instance_profile_name
  name_prefix                = "hub"
}
