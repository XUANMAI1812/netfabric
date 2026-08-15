import subprocess
import json

def get_terraform_output(env_path):
    result = subprocess.run(
        ["terraform", "output", "-json"],
        cwd=env_path,
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)

def main():
    hub = get_terraform_output("../terraform/envs/hub")
    spoke = get_terraform_output("../terraform/envs/spoke")

    targets = {
        "hub_test_host_id":       hub["test_host_instance_id"]["value"],
        "hub_private_ip":         hub["test_host_private_ip"]["value"],
        "spoke_test_host_id":     spoke["test_host_instance_id"]["value"],
        "spoke_private_ip":       spoke["test_host_private_ip"]["value"],
        "hub_nat_instance_id":    hub["instance_id"]["value"],
        "spoke_nat_instance_id":  spoke["instance_id"]["value"],
        "hub_public_ip":          hub["public_ip"]["value"],
        "spoke_public_ip":        spoke["public_ip"]["value"],

        # Backbone ip tự đặt nên vẫn phải hardcode
        "hub_backbone_ip":   "10.100.0.1",
        "spoke_backbone_ip": "10.100.0.2",
    }

    with open("targets.json", "w") as f:
        json.dump(targets, f, indent=2)

    print(json.dumps(targets, indent=2))
    return targets

if __name__ == "__main__":
    main()
