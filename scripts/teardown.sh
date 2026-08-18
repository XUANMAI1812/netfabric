#!/bin/bash
set -euo pipefail

echo "Đang huỷ hạ tầng spoke..."
cd ~/netfabric/terraform/envs/spoke
terraform destroy -auto-approve

echo "Đang huỷ hạ tầng hub..."
cd ~/netfabric/terraform/envs/hub
terraform destroy -auto-approve

echo "Xong. Kiểm tra Cost Explorer để xác nhận nha hihi"
