import sys
import requests
import logging
from typing import List
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.ERROR)


def get_ip_ranges(region: str = None, managed_service: str = "S3"):
    function_name = sys._getframe().f_code.co_name

    ip_ranges = requests.get("https://ip-ranges.amazonaws.com/ip-ranges.json").json()[
        "prefixes"
    ]
    managed_service_ips = [
        item["ip_prefix"] for item in ip_ranges if item["service"] == managed_service
    ]
    region_ips = [item["ip_prefix"] for item in ip_ranges if item["region"] == region]

    managed_service_region_ips = []

    for ip in region_ips:
        if ip in managed_service_ips:
            managed_service_region_ips.append(ip)

    out_str = " "

    managed_service_region_ips_str = " "

    managed_service_region_ips_str = out_str.join(managed_service_region_ips)
    print(
        function_name,
        "(): managed_service_region_ips_str = ",
        managed_service_region_ips_str,
    )

    return managed_service_region_ips_str


def install_stress_ng_on_pod(node_key: str, node_values: List[str]):
    """Runs SSM command InstallStressNG.yml on all targets with specified tag key and value"""

    session = boto3.Session()
    ssm = session.client("ssm", "us-east-1")

    try:
        ssm.send_command(
            Targets=[{"Key": node_key, "Values": node_values}],
            DocumentName="InstallStressNG",
        )
    except ClientError as e:
        logging.error(e)
        return False

    return True
