output "vpc_id" { value = aws_vpc.this.id }
output "public_subnet_id" { value = aws_subnet.public.id }
output "private_subnet_id" { value = aws_subnet.private.id }
output "private_route_table_id" { value = aws_route_table.private.id }
output "vpc_cidr" { value = var.vpc_cidr }
output "nat_bastion_sg_id" { value = aws_security_group.nat_bastion.id }  # module nat-instance ở Phần 2 cần ID này
