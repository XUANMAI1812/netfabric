import subprocess
import json
import time
import datetime

with open("targets.json") as f:
    TARGETS = json.load(f)

REGION_OF = {
    "hub-private": "ap-southeast-1", "hub-public": "ap-southeast-1",
    "spoke-private": "ap-southeast-2", "spoke-public": "ap-southeast-2",
}

SRC_INSTANCE = {
    "hub-private":   TARGETS["hub_test_host_id"],
    "spoke-private": TARGETS["spoke_test_host_id"],
    "hub-public":    TARGETS["hub_nat_instance_id"],
    "spoke-public":  TARGETS["spoke_nat_instance_id"],
}

DST_IP = {
    "hub-private":    TARGETS["hub_private_ip"],
    "spoke-private":  TARGETS["spoke_private_ip"],
    "hub-backbone":   TARGETS["hub_backbone_ip"],
    "spoke-backbone": TARGETS["spoke_backbone_ip"],
}

# ma trận kỳ vọng
EXPECTED_MATRIX = [
    {"src": "hub-private", "dst": "spoke-private", "port": None, "expect_allow": True,
     "reason": "Ping tới private IP thật của spoke qua WireGuard tunnel phải thành công"},
    {"src": "hub-private", "dst": "spoke-backbone", "port": None, "expect_allow": True,
     "reason": "Ping tới backbone IP (10.100.0.2) của spoke qua tunnel phải thành công"},
    {"src": "hub-public", "dst": "hub-private", "port": 22, "expect_allow": False,
     "reason": "Không SSH trực tiếp từ public vào private — SG test-host không mở port 22"},
    {"src": "hub-private", "dst": "spoke-private", "port": 5201, "expect_allow": True,
     "reason": "SG test-host mở TCP 5201 (iperf3) cho CIDR VPC bên kia — Phần 5.2"},
    {"src": "spoke-private", "dst": "hub-private", "port": 5201, "expect_allow": True,
     "reason": "Đối xứng với case trên — kiểm tra cả 2 chiều"},
]

IPERF_PORT = 5201
IPERF_UNIT_NAME = "netfabric-iperf3-connectivity-check"

def run_ssm_command(instance_id, command, region):
    result = subprocess.run([
        "aws", "ssm", "send-command",
        "--instance-ids", instance_id,
        "--document-name", "AWS-RunShellScript",
        "--parameters", json.dumps({"commands": [command]}),
        "--region", region,
        "--profile", "netfabric",
        "--output", "json"
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"aws ssm send-command thất bại: {result.stderr.strip()}")
    return json.loads(result.stdout)["Command"]["CommandId"]

def wait_for_result(instance_id, command_id, region, timeout=30, poll_interval=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run([
            "aws", "ssm", "get-command-invocation",
            "--command-id", command_id,
            "--instance-id", instance_id,
            "--region", region,
            "--profile", "netfabric",
            "--output", "json"
        ], capture_output=True, text=True)
        if result.returncode == 0:
            invocation = json.loads(result.stdout)
            if invocation.get("Status") in ("Success", "Failed", "Cancelled", "TimedOut"):
                return invocation.get("StandardOutputContent", "")
        time.sleep(poll_interval)
    raise TimeoutError(f"Command {command_id} không có kết quả sau {timeout}s")

# các case tét
def test_ping(src_label, dst_ip, count=3, timeout_s=5):
    cmd = f"ping -c {count} -W {timeout_s} {dst_ip} > /dev/null 2>&1 && echo SUCCESS || echo FAIL"
    command_id = run_ssm_command(SRC_INSTANCE[src_label], cmd, REGION_OF[src_label])
    output = wait_for_result(SRC_INSTANCE[src_label], command_id, REGION_OF[src_label])
    return "SUCCESS" in output

def test_tcp_port(src_label, dst_ip, port, timeout_s=3):
    cmd = (f"timeout {timeout_s} bash -c 'echo > /dev/tcp/{dst_ip}/{port}' "
           "&& echo SUCCESS || echo FAIL")
    command_id = run_ssm_command(SRC_INSTANCE[src_label], cmd, REGION_OF[src_label])
    output = wait_for_result(SRC_INSTANCE[src_label], command_id, REGION_OF[src_label])
    return "SUCCESS" in output

def start_iperf_listener(label):
    """Bật iperf3 server tạm trên test host"""
    cmd = (
        f"sudo systemctl reset-failed {IPERF_UNIT_NAME} 2>/dev/null; "
        f"sudo systemd-run --unit={IPERF_UNIT_NAME} "
        f"--description='connectivity_matrix.py: iperf3 server tam thoi de test TCP {IPERF_PORT}' "
        f"/usr/bin/iperf3 -s -p {IPERF_PORT}"
    )
    command_id = run_ssm_command(SRC_INSTANCE[label], cmd, REGION_OF[label])
    wait_for_result(SRC_INSTANCE[label], command_id, REGION_OF[label], timeout=30)
    time.sleep(2)

def stop_iperf_listener(label):
    cmd = f"sudo systemctl stop {IPERF_UNIT_NAME} 2>/dev/null || true"
    command_id = run_ssm_command(SRC_INSTANCE[label], cmd, REGION_OF[label])
    wait_for_result(SRC_INSTANCE[label], command_id, REGION_OF[label], timeout=30)

def main():
    listener_labels = sorted({c["dst"] for c in EXPECTED_MATRIX if c["port"] is not None})

    print(f"Bật iperf3 server tạm")
    for label in listener_labels:
        start_iperf_listener(label)

    try:
        results = []
        for case in EXPECTED_MATRIX:
            dst_ip = DST_IP[case["dst"]]
            actual_allow = (test_ping(case["src"], dst_ip) if case["port"] is None
                             else test_tcp_port(case["src"], dst_ip, case["port"]))

            passed = actual_allow == case["expect_allow"]
            results.append({
                **case,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "actual_result": "allow" if actual_allow else "deny",
                "pass": passed,
            })
            port_label = f":{case['port']}" if case["port"] else ""
            print(f"[{'PASS' if passed else 'FAIL'}] {case['src']} -> {case['dst']}{port_label} "
                  f"(expect_allow={case['expect_allow']}, actual_allow={actual_allow})")

        report = {
            "test_run": datetime.datetime.utcnow().isoformat(),
            "total_cases": len(results),
            "passed": sum(1 for r in results if r["pass"]),
            "failed": sum(1 for r in results if not r["pass"]),
            "results": results,
        }

        with open("../reports/connectivity_matrix.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nĐã chạy {len(results)} test case ({report['passed']} pass, "
              f"{report['failed']} fail) — xem chi tiết ở reports/connectivity_matrix.json")
    finally:
        print("Tắt iperf3 server tạm...")
        for label in listener_labels:
            stop_iperf_listener(label)

if __name__ == "__main__":
    main()
