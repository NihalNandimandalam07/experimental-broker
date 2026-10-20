import logging
import boto3

from time import sleep
from kafka import KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic, ConfigResource, ConfigResourceType
from typing import List
from logzero import logger
from botocore.exceptions import ClientError
from activities.kafka.shared import get_broker_endpoints


def blackhole_kafka(
    region: str = None,
    msk_cluster: str = None,
    node_key: str = None,
    node_values: List[str] = None,
):
    """Runs SSM command BlackHoleKafka.yml on all targets with specified tag key and value"""

    session = boto3.Session()
    ssm = session.client("ssm", region)

    kafkanodes = get_broker_endpoints(region, msk_cluster)

    try:
        ssm.send_command(
            DocumentName="BlackHoleKafka",
            Targets=[{"Key": node_key, "Values": node_values}],
            Parameters={
                "kafkanodes": [kafkanodes],
            },
            TimeoutSeconds=120,
            DocumentVersion="1",
            MaxErrors="10",
            MaxConcurrency="1",
        )
    except ClientError as e:
        logging.error(e)


def remove_topic(msk_hosts, topic: str, duration: str):
    admin_client = KafkaAdminClient(msk_hosts)
    describe_topic = admin_client.describe_topics([topic])
    topic_configs = admin_client.describe_configs(
        [ConfigResource(name=topic, resource_type=ConfigResourceType(2))]
    )
    replica_map = {}
    for element in describe_topic[0]["partitions"]:
        replica_map[element["partition"]] = element["replicas"]
    topic_config = {}
    for config_pair in topic_configs[0].resources[0][4]:
        topic_config[config_pair[0]] = config_pair[1]
    new_topic = NewTopic(
        name=topic,
        num_partitions=-1,
        replication_factor=-1,
        replica_assignments=replica_map,
        topic_configs=topic_config,
    )
    destroy_resp = admin_client.delete_topics([topic])
    logger.info(destroy_resp)
    sleep(int(duration))
    describe_topic = admin_client.describe_topics([topic])
    create_resp = admin_client.create_topics([new_topic])
    logger.info(create_resp)
    describe_topic = admin_client.describe_topics([topic])

    return destroy_resp, create_resp
