terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region  = "ap-southeast-2"
  profile = "netfabric"
}

module "vpc" {
  source               = "../../modules/vpc"
  region               = "ap-southeast-2"
  vpc_cidr             = "10.1.0.0/16"
  public_subnet_cidr   = "10.1.1.0/24"
  private_subnet_cidr  = "10.1.2.0/24"
  availability_zone    = "ap-southeast-2a"
  name_prefix          = "spoke"
  peer_vpc_cidr        = "10.0.0.0/16"
  peer_public_ip  = var.peer_public_ip
}

module "nat_instance" {
  source             = "../../modules/nat-instance"
  public_subnet_id   = module.vpc.public_subnet_id
  security_group_id  = module.vpc.nat_bastion_sg_id
  name_prefix        = "spoke"
  iam_instance_profile_name  = module.iam.instance_profile_name
}

module "iam" {
  source      = "../../modules/iam"
  name_prefix = "spoke"
}
