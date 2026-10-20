import boto3
import os
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from logzero import logger


def get_opensearch_client(opensearch_config):
    if "http:" in opensearch_config["host"]:
        logger.error("Malformed Opensearch URL: remove 'http:' prefix ")
    host = opensearch_config["host"]
    credentials = boto3.Session().get_credentials()
    region = os.environ.get(
        "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    )
    auth = AWSV4SignerAuth(credentials, region, "es")

    client = OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
    )
    return client


def upload_experiment_journal(journal, output_config):
    client = get_opensearch_client(output_config)
    if not client.indices.exists(output_config["index"]):
        create_index(client=client, index=output_config["index"])
    client.index(index=output_config["index"], body=journal)


def create_index(client, index):
    index_body = {"settings": {"index": {"number_of_shards": 4}}}
    client.indices.create(index=index, body=index_body)
