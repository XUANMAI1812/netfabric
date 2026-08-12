#!/bin/bash
set -euxo pipefail

echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
sysctl -p

IFACE=$(ip route show default | awk '{print $5}')

# thay đc nguồn của traffic private subnet thành IP của NAT instance khi ra internet
iptables -t nat -A POSTROUTING -o "$IFACE" -j MASQUERADE
iptables -A FORWARD -i "$IFACE" -o "$IFACE" -j ACCEPT

yum install -y iptables-services
service iptables save
systemctl enable iptables

# Cài lại cho chắc
yum install -y amazon-ssm-agent
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent
yum install -y wireguard-tools

if dnf search fail2ban 2>/dev/null | grep -qi fail2ban; then
  yum install -y fail2ban
  systemctl enable fail2ban
  systemctl start fail2ban
else
  echo "fail2ban không có trong repo AL2023 hiện tại, cài thủ công từ source nếu cần" >> /var/log/netfabric-userdata.log
fi
