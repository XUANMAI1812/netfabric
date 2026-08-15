resource "aws_security_group" "test_host" {
  name_prefix = "${var.name_prefix}-test-host-"
  vpc_id      = var.vpc_id

  ingress {
    description = "ICMP ping from peer VPC via WireGuard tunnel"
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = [var.peer_vpc_cidr]
  }

  ingress {
    description = "iperf3 from peer VPC via WireGuard tunnel"
    from_port   = 5201
    to_port     = 5201
    protocol    = "tcp"
    cidr_blocks = [var.peer_vpc_cidr]
  }

  # K có ingress port 22, vào = ssm
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]  # cần ra ngoài qua NAT instance để gọi SSM endpoint (443)
  }

  tags = { Name = "${var.name_prefix}-test-host-sg" }
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

resource "aws_instance" "test_host" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.micro"
  subnet_id              = var.private_subnet_id
  vpc_security_group_ids = [aws_security_group.test_host.id]
  iam_instance_profile   = var.iam_instance_profile_name

  user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail
    yum install -y amazon-ssm-agent iperf3
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent
  EOF

  tags = { Name = "${var.name_prefix}-test-host" }
}
