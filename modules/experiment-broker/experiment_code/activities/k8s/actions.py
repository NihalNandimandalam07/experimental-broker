import json
import os
import sys
import boto3
import time
import logging
import inspect
import threading
from logzero import logger

from activities.enums import ParameterMapFailuremode
from chaoslib import ActivityFailed
from datetime import datetime, timedelta
from typing import List
from botocore.exceptions import ClientError
from activities.ec2.shared import get_test_instance_ids
from chaosk8s.pod.actions import terminate_pods

from kubernetes import client, config
from activities.k8s.shared import (
    get_eks_api_client,
    patch_eks_deployment,
    get_eks_deployment,
    k8s_api_stressor,
    get_pod_ip,
)
from activities.ssm.shared import (
    run_ssm_doc,
    run_ssm_doc_multistage,
    process_ssm_response,
)


def stress_eks_api(
    api_stress_duration: str,
    intensity: str,
    region: str = "us-east-1",
):
    client = boto3.client("eks", region)
    try:
        target = client.list_clusters()["clusters"][0]
    except Exception as e:
        logger.error(e)
        raise ActivityFailed(e)
    end = datetime.now() + timedelta(minutes=int(api_stress_duration))
    threads = []
    while datetime.now() < end:
        threads = [x for x in threads if x.is_alive()]
        while len(threads) < intensity:
            temp = threading.Thread(target=k8s_api_stressor, args=(end, region, target))
            temp.start()
            threads.append(temp)
    else:
        [x.join() for x in threads]
    return True


def kill_pods(
    cluster_name: str,
    name_space: str,
    pod_name_pattern: str,
    num_pods_to_kill: str = "1",
    test_target_type: str = "RANDOM",
    region: str = "us-east-1",
):
    function_name = inspect.stack()[0][3]
    logger.info(f"{function_name}(): cluster_name={cluster_name}")
    logger.info(f"{function_name}(): name_space={name_space}")
    logger.info(f"{function_name}(): pod_name_pattern={pod_name_pattern}")
    try:
        k8s_params = dict(
            name_pattern=pod_name_pattern,
            ns=name_space,
            qty=int(num_pods_to_kill),
            rand=test_target_type == "RANDOM",
            all=test_target_type == "ALL",
        )

        logger.info(
            f"{function_name}(): calling get_eks_api_client(cluster_name={cluster_name}, region={region})"
        )
        api_client = get_eks_api_client(cluster_name=cluster_name, region=region)
        os.environ["KUBERNETES_HOST"] = api_client.configuration.host
        os.environ["KUBERNETES_API_KEY"] = api_client.configuration.api_key[
            "authorization"
        ]
        os.environ[
            "KUBERNETES_API_KEY_PREFIX"
        ] = api_client.configuration.api_key_prefix["authorization"]

        logger.info(f"{function_name}(): terminating pods")
        pod_del = terminate_pods(**k8s_params)
        logger.info(f"{function_name}(): Killed pods: {pod_del}")

    except Exception as e:
        logger.error(e)
        raise

    return {"pods_terminated": pod_del}


def eks_update_image_tag(
    cluster_name: str,
    failed_image_tag: str,
    pod_name_pattern: str,
    name_space: str,
    region: str = "us-east-1",
):
    function_name = inspect.stack()[0][3]
    deployment_name = pod_name_pattern + "-" + name_space

    deployment = get_eks_deployment(
        cluster_name=cluster_name,
        region=region,
        namespace=name_space,
        name=deployment_name,
    )

    current_image = deployment.spec.template.spec.containers[0].image
    logger.info(f"{function_name}(): current_image={current_image}")
    split_image = current_image.split("-")

    current_tag = split_image[-1]
    logger.info(f"{function_name}(): current_tag={current_tag}")

    split_image[-1] = failed_image_tag
    new_image = "-".join(split_image)
    logger.info(f"{function_name}(): Setting image to {new_image}")
    current_image = deployment.spec.template.spec.containers[0].image = new_image

    resp = patch_eks_deployment(
        cluster_name=cluster_name,
        region=region,
        namespace=name_space,
        deployment=deployment,
    )
    logger.info(f"{function_name}(): {resp}")

    return resp


def pod_kill_process_in_container(
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    num_containers_to_target: str = "1",
    region: str = "us-east-1",
    pod_kill_process_name: str = "",
    pod_kill_process_signal: str = "SIGKILL",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): : test_instance_ids={test_instance_ids}")

    parameters = {
        "numContainersToTarget": [
            num_containers_to_target,
        ],
        "containerNamePattern": [
            container_name_pattern,
        ],
        "signal": [
            pod_kill_process_signal,
        ],
        "processName": [
            pod_kill_process_name,
        ],
    }
    try:
        results = run_ssm_doc(
            document_name="PodKillProcessInContainer",
            test_instance_ids=test_instance_ids,
            doc_parameters=parameters,
            region=region,
        )
    except ClientError as err:
        logger.error(err)
        raise

    failed = [x for x in results if x["status"] != "Success"]
    if failed:
        for failure in failed:
            output = ";".join([x["output"] for x in failure["output"]])
            logger.error(
                f"{function_name}(): {failure['instanceid']} failed in ssm execution with output {output}"
            )
        raise ActivityFailed(
            f"{function_name}(): SSM Execution failed: {json.dumps(failed)}"
        )
    return results


def pod_stress_packet_loss(
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    num_containers_to_target: str = "1",
    region: str = "us-east-1",
    port_type: str = "sport",
    port_number: str = "0",
    loss: str = "90",
    duration: str = "60",
    interface: str = "eth0",
    max_duration: str = "900",
    pod_stress_packet_loss_parameter_map: dict[str, dict] = {},
    pod_stress_packet_loss_failure_mode: bool = True,
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "numContainersToTarget": [num_containers_to_target],
        "containerNamePattern": [container_name_pattern],
        "duration": [duration],
        "interface": [interface],
        "portType": [port_type],
        "portNumber": [port_number],
        "loss": [loss],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not pod_stress_packet_loss_parameter_map:
        pod_stress_packet_loss_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(pod_stress_packet_loss_parameter_map[x]["duration"][0])
        for x in pod_stress_packet_loss_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="PodStressPacketLoss",
        failure_mode=ParameterMapFailuremode[pod_stress_packet_loss_failure_mode],
        param_map=pod_stress_packet_loss_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results


def pod_stress_network_latency(
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    num_containers_to_target: str = "1",
    region: str = "us-east-1",
    port_type: str = "sport",
    port_number: str = "0",
    network_delay: str = "100",
    duration: str = "60",
    interface: str = "eth0",
    max_duration: str = "900",
    pod_stress_network_latency_parameter_map: dict[str, dict] = {},
    pod_stress_network_latency_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "numContainersToTarget": [num_containers_to_target],
        "containerNamePattern": [container_name_pattern],
        "duration": [duration],
        "interface": [interface],
        "portType": [port_type],
        "portNumber": [port_number],
        "delay": [network_delay],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not pod_stress_network_latency_parameter_map:
        pod_stress_network_latency_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(pod_stress_network_latency_parameter_map[x]["duration"][0])
        for x in pod_stress_network_latency_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="PodStressNetworkLatency",
        failure_mode=ParameterMapFailuremode[pod_stress_network_latency_failure_mode],
        param_map=pod_stress_network_latency_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results


def pod_stress_network_utilization(
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    num_containers_to_target: str = "1",
    region: str = "us-east-1",
    port_type: str = "sport",
    port_number: str = "0",
    network_rate: str = "100",
    duration: str = "60",
    interface: str = "eth0",
    max_duration: str = "900",
    pod_stress_network_utilization_parameter_map: dict[str, dict] = {},
    pod_stress_network_utilization_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "numContainersToTarget": [num_containers_to_target],
        "containerNamePattern": [container_name_pattern],
        "duration": [duration],
        "interface": [interface],
        "portType": [port_type],
        "portNumber": [port_number],
        "rate": [network_rate],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not pod_stress_network_utilization_parameter_map:
        pod_stress_network_utilization_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(pod_stress_network_utilization_parameter_map[x]["duration"][0])
        for x in pod_stress_network_utilization_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="PodStressNetworkUtilization",
        failure_mode=ParameterMapFailuremode[
            pod_stress_network_utilization_failure_mode
        ],
        param_map=pod_stress_network_utilization_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results


def pod_stress_cpu(
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    num_containers_to_target: str = "1",
    region: str = "us-east-1",
    duration: str = "60",
    max_duration: str = "900",
    pod_cpu: str = "80",
    pod_stress_cpu_parameter_map: dict[str, dict] = {},
    pod_stress_cpu_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "numContainersToTarget": [num_containers_to_target],
        "containerNamePattern": [container_name_pattern],
        "duration": [duration],
        "cpu": [pod_cpu],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not pod_stress_cpu_parameter_map:
        pod_stress_cpu_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(pod_stress_cpu_parameter_map[x]["duration"][0])
        for x in pod_stress_cpu_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="PodStressCPU",
        failure_mode=ParameterMapFailuremode[pod_stress_cpu_failure_mode],
        param_map=pod_stress_cpu_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results


def pod_stress_memory(
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    num_containers_to_target: str = "1",
    region: str = "us-east-1",
    pod_stress_memory_duration: str = "60",
    max_duration: str = "900",
    pod_stress_memory_percent_per_worker: str = "50",
    pod_stress_memory_number_of_workers: str = "1",
    pod_stress_memory_parameter_map: dict[str, dict] = {},
    pod_stress_memory_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "numContainersToTarget": [num_containers_to_target],
        "containerNamePattern": [container_name_pattern],
        "duration": [pod_stress_memory_duration],
        "numberOfWorkers": [pod_stress_memory_number_of_workers],
        "memoryPercentagePerWorker": [pod_stress_memory_percent_per_worker],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not pod_stress_memory_parameter_map:
        pod_stress_memory_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(pod_stress_memory_parameter_map[x]["duration"][0])
        for x in pod_stress_memory_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="PodStressMemory",
        failure_mode=ParameterMapFailuremode[pod_stress_memory_failure_mode],
        param_map=pod_stress_memory_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results


def pod_stress_cpu(
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    num_containers_to_target: str = "1",
    region: str = "us-east-1",
    pod_stress_cpu_duration: str = "60",
    max_duration: str = "900",
    pod_stress_cpu_percentage: str = "50",
    pod_stress_memory_parameter_map: dict[str, dict] = {},
    pod_stress_memory_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "numContainersToTarget": [num_containers_to_target],
        "containerNamePattern": [container_name_pattern],
        "duration": [pod_stress_cpu_duration],
        "cpu": [pod_stress_cpu_percentage],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not pod_stress_memory_parameter_map:
        pod_stress_memory_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(pod_stress_memory_parameter_map[x]["duration"][0])
        for x in pod_stress_memory_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="PodStressCPU",
        failure_mode=ParameterMapFailuremode[pod_stress_memory_failure_mode],
        param_map=pod_stress_memory_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results


def pod_exhaust_root_vol(
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    num_containers_to_target: str = "1",
    region: str = "us-east-1",
    duration: str = "60",
    max_duration: str = "900",
    pod_exhaust_root_vol_parameter_map: dict[str, dict] = {},
    pod_exhaust_root_vol_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "numContainersToTarget": [num_containers_to_target],
        "containerNamePattern": [container_name_pattern],
        "duration": [duration],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not pod_exhaust_root_vol_parameter_map:
        pod_exhaust_root_vol_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(pod_exhaust_root_vol_parameter_map[x]["duration"][0])
        for x in pod_exhaust_root_vol_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="PodDiskVolumeExhaustion",
        failure_mode=ParameterMapFailuremode[pod_exhaust_root_vol_failure_mode],
        param_map=pod_exhaust_root_vol_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results


def delete_pod_ssm(
    name_space: str,
    pod_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    delete_pod_ssm_parameter_map: dict[str, dict] = {},
    delete_pod_ssm_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "namespace": [name_space],
        "podNamePatter": [pod_name_pattern],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not delete_pod_ssm_parameter_map:
        delete_pod_ssm_parameter_map["default"] = def_ssm_doc_params

    results = run_ssm_doc_multistage(
        doc_name="DeletePod",
        failure_mode=ParameterMapFailuremode[delete_pod_ssm_failure_mode],
        param_map=delete_pod_ssm_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results


def pod_termination_crash(
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    num_containers_to_target: str = "1",
    pod_termination_crash_parameter_map: dict[str, dict] = {},
    pod_termination_crash_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "numContainersToTarget": [
            num_containers_to_target,
        ],
        "containerNamePattern": [
            container_name_pattern,
        ],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not pod_termination_crash_parameter_map:
        pod_termination_crash_parameter_map["default"] = def_ssm_doc_params

    results = run_ssm_doc_multistage(
        doc_name="PodTerminationCrash",
        failure_mode=ParameterMapFailuremode[pod_termination_crash_failure_mode],
        param_map=pod_termination_crash_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results


def pod_blackhole_by_port(
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    num_containers_to_target: str = "1",
    region: str = "us-east-1",
    pod_blackhole_by_port_protocol: str = "tcp udp",
    pod_blackhole_by_port_source_ports: str = "",
    pod_blackhole_by_port_destination_ports: str = "",
    pod_blackhole_by_port_direction: str = "BOTH",
    pod_blackhole_by_port_duration: str = "60",
    max_duration: str = "900",
    pod_blackhole_by_port_parameter_map: dict[str, dict] = {},
    pod_blackhole_by_port_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "numContainersToTarget": [num_containers_to_target],
        "containerNamePattern": [container_name_pattern],
        "duration": [pod_blackhole_by_port_duration],
        "protocol": [pod_blackhole_by_port_protocol],
        "sourcePorts": [pod_blackhole_by_port_source_ports],
        "destinationPorts": [pod_blackhole_by_port_destination_ports],
        "direction": [pod_blackhole_by_port_direction],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not pod_blackhole_by_port_parameter_map:
        pod_blackhole_by_port_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(pod_blackhole_by_port_parameter_map[x]["duration"][0])
        for x in pod_blackhole_by_port_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="PodBlackholeByPort",
        failure_mode=ParameterMapFailuremode[pod_blackhole_by_port_failure_mode],
        param_map=pod_blackhole_by_port_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results


def pod_blackhole_by_ip(
    pod_blackhole_ip: str,
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    num_containers_to_target: str = "1",
    region: str = "us-east-1",
    pod_blackhole_by_ip_port_protocol: str = "tcp udp",
    pod_blackhole_by_ip_direction: str = "BOTH",
    pod_blackhole_by_ip_duration: str = "60",
    max_duration: str = "900",
    pod_blackhole_by_ip_parameter_map: dict[str, dict] = {},
    pod_blackhole_by_ip_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "numContainersToTarget": [num_containers_to_target],
        "containerNamePattern": [container_name_pattern],
        "duration": [pod_blackhole_by_ip_duration],
        "protocol": [pod_blackhole_by_ip_port_protocol],
        "sourceIP": [pod_blackhole_ip],
        "destinationIP": [pod_blackhole_ip],
        "direction": [pod_blackhole_by_ip_direction],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not pod_blackhole_by_ip_parameter_map:
        pod_blackhole_by_ip_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(pod_blackhole_by_ip_parameter_map[x]["duration"][0])
        for x in pod_blackhole_by_ip_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="PodBlackholeByIP",
        failure_mode=ParameterMapFailuremode[pod_blackhole_by_ip_failure_mode],
        param_map=pod_blackhole_by_ip_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results


def pod_blackhole_by_name(
    cluster_name: str,
    blacklist_pod_name_pattern: str,
    container_name_pattern: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    num_containers_to_target: str = "1",
    region: str = "us-east-1",
    pod_blackhole_by_name_protocol: str = "tcp udp",
    pod_blackhole_by_name_direction: str = "BOTH",
    pod_blackhole_by_name_duration: str = "60",
    max_duration: str = "900",
    pod_blackhole_by_name_parameter_map: dict[str, dict] = {},
    pod_blackhole_by_name_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    logger.info(
        f"{function_name}(): calling get_eks_api_client(cluster_name={cluster_name}, region={region})"
    )
    api_client = get_eks_api_client(cluster_name=cluster_name, region=region)
    pod_ips_blacklist = get_pod_ip(blacklist_pod_name_pattern, api_client=api_client)

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "numContainersToTarget": [num_containers_to_target],
        "containerNamePattern": [container_name_pattern],
        "duration": [pod_blackhole_by_name_duration],
        "protocol": [pod_blackhole_by_name_protocol],
        "direction": [pod_blackhole_by_name_direction],
        "sourceIP": [pod_ips_blacklist],
        "destinationIP": [pod_ips_blacklist],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not pod_blackhole_by_name_parameter_map:
        pod_blackhole_by_name_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(pod_blackhole_by_name_parameter_map[x]["duration"][0])
        for x in pod_blackhole_by_name_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="PodBlackholeByPort",
        failure_mode=ParameterMapFailuremode[pod_blackhole_by_name_failure_mode],
        param_map=pod_blackhole_by_name_parameter_map,
        def_instance_params=def_instance_params,
        def_doc_params=def_ssm_doc_params,
        region=region,
    )
    if len([x[2] for x in results if x[1] != "success"]) > 0:
        logger.error(
            f"{function_name}(): Failed SSM runs with output: {json.dumps(results)}"
        )
        raise ActivityFailed(f"Failed SSM runs with output: {json.dumps(results)}")
    return results
