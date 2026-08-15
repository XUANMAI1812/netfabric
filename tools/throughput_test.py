import subprocess
import json
import time
import datetime

with open("targets.json") as f:
    TARGETS = json.load(f)

REGION_OF = {
    "hub": "ap-southeast-1",
    "spoke": "ap-southeast-2",
}

TEST_HOST_ID = {
    "hub": TARGETS["hub_test_host_id"],
    "spoke": TARGETS["spoke_test_host_id"],
}

PRIVATE_IP = {
    "hub": TARGETS["hub_private_ip"],
    "spoke": TARGETS["spoke_private_ip"],
}

IPERF_PORT = 5201
IPERF_UNIT_NAME = "netfabric-iperf3-server"


def run_ssm_command(instance_id, command, region, timeout=30, poll_interval=2):
    send = subprocess.run([
        "aws", "ssm", "send-command",
        "--instance-ids", instance_id,
        "--document-name", "AWS-RunShellScript",
        "--parameters", json.dumps({"commands": [command]}),
        "--region", region,
        "--profile", "netfabric",
        "--output", "json",
    ], capture_output=True, text=True)
    if send.returncode != 0:
        raise RuntimeError(f"aws ssm send-command thất bại: {send.stderr.strip()}")
    command_id = json.loads(send.stdout)["Command"]["CommandId"]

    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run([
            "aws", "ssm", "get-command-invocation",
            "--command-id", command_id,
            "--instance-id", instance_id,
            "--region", region,
            "--profile", "netfabric",
            "--output", "json",
        ], capture_output=True, text=True)
        if result.returncode == 0:
            invocation = json.loads(result.stdout)
            status = invocation.get("Status")
            if status == "Success":
                return invocation.get("StandardOutputContent", "")
            if status in ("Failed", "Cancelled", "TimedOut"):
                raise RuntimeError(
                    f"SSM command {command_id} kết thúc với status={status}: "
                    f"{invocation.get('StandardErrorContent', '').strip()}"
                )
        time.sleep(poll_interval)
    raise TimeoutError(f"Command {command_id} không có kết quả sau {timeout}s")


def start_iperf_server(label):
    cmd = (
        f"sudo systemctl reset-failed {IPERF_UNIT_NAME} 2>/dev/null; "
        f"sudo systemd-run --unit={IPERF_UNIT_NAME} "
        f"--description='netfabric throughput test iperf3 server' "
        f"/usr/bin/iperf3 -s -p {IPERF_PORT}"
    )
    run_ssm_command(TEST_HOST_ID[label], cmd, REGION_OF[label], timeout=30)
    time.sleep(3)


def stop_iperf_server(label):
    cmd = f"sudo systemctl stop {IPERF_UNIT_NAME} 2>/dev/null || true"
    run_ssm_command(TEST_HOST_ID[label], cmd, REGION_OF[label], timeout=30)


def run_iperf_client(src_label, dst_ip, duration=10):
    cmd = f"/usr/bin/iperf3 -c {dst_ip} -p {IPERF_PORT} -t {duration} -J"
    output = run_ssm_command(
        TEST_HOST_ID[src_label], cmd, REGION_OF[src_label],
        timeout=duration + 20, poll_interval=2,
    )
    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Không parse được output iperf3 -J từ {src_label}: {e}\n"
            f"Output thô: {output[:500]}"
        )
    return data


def main():
    print("Khởi động iperf3 server trên spoke test host...")
    start_iperf_server("spoke")
    try:
        print("Chạy iperf3 client từ hub test host tới spoke")
        result = run_iperf_client("hub", PRIVATE_IP["spoke"], duration=10)

        received = result["end"]["sum_received"]
        sent = result["end"]["sum_sent"]
        report = {
            "test_run": datetime.datetime.utcnow().isoformat(),
            "src": "hub-private-testhost",
            "dst": "spoke-private-testhost",
            "dst_ip": PRIVATE_IP["spoke"],
            "duration_s": result["start"]["test_start"]["duration"],
            "sent_mbps": round(sent["bits_per_second"] / 1_000_000, 2),
            "received_mbps": round(received["bits_per_second"] / 1_000_000, 2),
            "retransmits": sent.get("retransmits"),
        }

        with open("../reports/throughput.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"Throughput qua tunnel: {report['received_mbps']} Mbps "
              f"(sent {report['sent_mbps']} Mbps, retransmits={report['retransmits']})")
        print("Đã ghi ../reports/throughput.json")
    finally:
        print("Dừng iperf3 server trên spoke test host...")
        stop_iperf_server("spoke")


if __name__ == "__main__":
    main()
