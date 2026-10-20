import logging

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.ERROR)


def get_broker_endpoints(region: str = None, msk_cluster: str = None) -> list:
    endpoint_list = []

    session = boto3.Session()
    kafka = session.client("kafka", region)

    try:
        broker_list = kafka.list_nodes(ClusterArn=msk_cluster)
        for node in broker_list.get("NodeInfoList"):
            endpoint_list.append(node["BrokerNodeInfo"]["Endpoints"][0])
            endpoints = " ".join(endpoint_list)
    except ClientError as e:
        logging.error(e)
    return endpoints
