import logging
import base64
import boto3
import re
import inspect
from botocore.signers import RequestSigner
from typing import List

import boto3
import kubernetes.client
from kubernetes.client import AppsV1Api, V1DeploymentList
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

from logzero import logger

logging.basicConfig(level=logging.ERROR)


def k8s_api_stressor(end, region, target):
    client = boto3.client("eks", region)
    while datetime.now() < end:
        try:
            response = client.describe_cluster(name=target)
        except Exception as e:
            logger.error(f"{datetime.now()}: exception occurred during api stress: {e}")


def get_bearer_token(cluster_name, region, expires=60):
    STS_TOKEN_EXPIRES_IN = 60
    session = boto3.session.Session()

    client = session.client("sts", region_name=region)

    logger.error(f"{client.get_caller_identity()['Arn']}")
    service_id = client.meta.service_model.service_id

    signer = RequestSigner(
        service_id, region, "sts", "v4", session.get_credentials(), session.events
    )

    params = {
        "method": "GET",
        "url": "https://sts.{}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15".format(
            region
        ),
        "body": {},
        "headers": {"x-k8s-aws-id": cluster_name},
        "context": {},
    }

    signed_url = signer.generate_presigned_url(
        params, region_name=region, expires_in=STS_TOKEN_EXPIRES_IN, operation_name=""
    )

    base64_url = base64.urlsafe_b64encode(signed_url.encode("utf-8")).decode("utf-8")

    # remove any base64 encoding padding:
    token = "k8s-aws-v1." + re.sub(r"=*", "", base64_url)
    return token


def get_eks_api_client(cluster_name, region, expires=60, verify_ssl=False):
    logger.debug(f"get_eks_api_client(): getting bearer token via get_bearer_token()")
    bearer_token = get_bearer_token(
        cluster_name=cluster_name, region=region, expires=expires
    )

    logger.debug(f"get_eks_api_client(): creating eks session and client")
    s = boto3.Session(region_name=region)
    eks = s.client("eks")

    # get cluster details
    logger.debug(f"get_eks_api_client(): getting details for cluster {cluster_name}")
    cluster = eks.describe_cluster(name=cluster_name)

    cluster_ep = cluster["cluster"]["endpoint"]
    logger.debug(f"get_eks_api_client(): received details for cluster {cluster_name}")
    logger.debug(f"get_eks_api_client(): cluster endpoint {cluster_ep}")

    logger.debug(
        f"get_eks_api_client(): Creating kubernetes client using bearer token for auth"
    )
    configuration = kubernetes.client.Configuration()
    configuration.verify_ssl = verify_ssl
    configuration.api_key["authorization"] = bearer_token
    configuration.api_key_prefix["authorization"] = "Bearer"
    configuration.host = cluster_ep

    logger.debug(f"get_eks_api_client(): received details for cluster {cluster_name}")
    api_client = kubernetes.client.ApiClient(configuration)
    return api_client


def get_eks_deployment(cluster_name, region, namespace, name):
    api_client = get_eks_api_client(cluster_name=cluster_name, region=region)
    apps_v1: AppsV1Api = AppsV1Api(api_client=api_client)
    deployment = apps_v1.read_namespaced_deployment(name=name, namespace=namespace)

    return deployment


def patch_eks_deployment(
    cluster_name, region, deployment_name, namespace, name, deployment
):
    api_client = get_eks_api_client(cluster_name=cluster_name, region=region)
    apps_v1: AppsV1Api = AppsV1Api(api_client=api_client)

    resp = apps_v1.patch_namespaced_deployment(
        name=deployment_name, namespace=namespace, body=deployment
    )
    return resp


def get_pod_ip(podname, api_client):
    v1client = kubernetes.client.CoreV1Api(api_client=api_client)
    pods = v1client.list_pod_for_all_namespaces(
        watch=False, label_selector=f"app={podname}"
    )
    ips = [x.status.pod_ip for x in pods.items]
    return ips


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
