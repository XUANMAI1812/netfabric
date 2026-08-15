output "public_ip"   { value = module.nat_instance.public_ip }
output "instance_id" { value = module.nat_instance.instance_id }

output "test_host_instance_id" { value = module.test_host.instance_id }
output "test_host_private_ip"  { value = module.test_host.private_ip }

