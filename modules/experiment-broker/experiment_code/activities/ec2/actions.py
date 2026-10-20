import json
import os
import sys
import boto3
import time
import logging
import inspect
import threading
from logzero import logger

import boto3
from activities.enums import ParameterMapFailuremode
from chaoslib import ActivityFailed
from datetime import datetime, timedelta
from typing import List
from botocore.exceptions import ClientError
from activities.ec2.shared import (
    get_test_instance_ids,
    get_role_from_instance_profile,
    get_instance_profile_name,
)
from activities.ssm.shared import (
    run_ssm_doc,
    run_ssm_doc_multistage,
    process_ssm_response,
)


def ec2_stress_packet_loss(
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    ec2_stress_packet_port_type: str = "sport",
    ec2_stress_packet_port_number: str = "0",
    ec2_stress_packet_loss_percent: str = "90",
    ec2_stress_packet_duration: str = "60",
    ec2_stress_packet_interface: str = "eth0",
    max_duration: str = "900",
    ec2_stress_packet_loss_parameter_map: dict[str, dict] = {},
    ec2_stress_packet_loss_failure_mode: str = "FailFast",
):
    function_name = inspect.stack()[0][3]

    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
        region=region,
    )

    logger.info(f"{function_name}(): test_instance_ids={test_instance_ids}")

    def_ssm_doc_params = {
        "duration": [ec2_stress_packet_duration],
        "interface": [ec2_stress_packet_interface],
        "portType": [ec2_stress_packet_port_type],
        "portNumber": [ec2_stress_packet_port_number],
        "loss": [ec2_stress_packet_loss_percent],
    }

    param_map = {}
    for sev_level in ec2_stress_packet_loss_parameter_map.keys():
        sev_params = {
            "duration": [
                ec2_stress_packet_loss_parameter_map[sev_level].get(
                    "ec2_stress_packet_duration",
                    ec2_stress_packet_duration,
                )
            ],
            "interface": [
                ec2_stress_packet_loss_parameter_map[sev_level].get(
                    "ec2_stress_packet_interface",
                    ec2_stress_packet_interface,
                )
            ],
            "portType": [
                ec2_stress_packet_loss_parameter_map[sev_level].get(
                    "ec2_stress_packet_port_type",
                    ec2_stress_packet_port_type,
                )
            ],
            "portNumber": [
                ec2_stress_packet_loss_parameter_map[sev_level].get(
                    "ec2_stress_packet_port_number",
                    ec2_stress_packet_port_number,
                )
            ],
            "loss": [
                ec2_stress_packet_loss_parameter_map[sev_level].get(
                    "ec2_stress_packet_loss_percent",
                    ec2_stress_packet_loss_percent,
                )
            ],
        }
        param_map[sev_level] = sev_params

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not param_map:
        param_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(param_map[x].get("duration", ec2_stress_packet_duration)[0])
        for x in param_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="StressPacketLoss",
        failure_mode=ParameterMapFailuremode[ec2_stress_packet_loss_failure_mode],
        param_map=param_map,
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


def ec2_stress_network_latency(
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    ec2_stress_network_latency_port_type: str = "sport",
    ec2_stress_network_latency_port_number: str = "0",
    ec2_stress_network_latency_network_delay: str = "100",
    ec2_stress_network_latency_duration: str = "60",
    ec2_stress_network_latency_interface: str = "eth0",
    max_duration: str = "900",
    ec2_stress_network_latency_parameter_map: dict[str, dict] = {},
    ec2_stress_network_latency_failure_mode: str = "FailFast",
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
        "duration": [ec2_stress_network_latency_duration],
        "interface": [ec2_stress_network_latency_interface],
        "portType": [ec2_stress_network_latency_port_type],
        "ports": [ec2_stress_network_latency_port_number],
        "delay": [ec2_stress_network_latency_network_delay],
    }

    param_map = {
        x: {
            "duration": [
                x.get(
                    "ec2_stress_network_latency_duration",
                    ec2_stress_network_latency_duration,
                )
            ],
            "interface": [
                x.get(
                    "ec2_stress_network_latency_interface",
                    ec2_stress_network_latency_interface,
                )
            ],
            "portType": [
                x.get(
                    "ec2_stress_network_latency_port_type",
                    ec2_stress_network_latency_port_type,
                )
            ],
            "ports": [
                x.get(
                    "ec2_stress_network_latency_port_number",
                    ec2_stress_network_latency_port_number,
                )
            ],
            "delay": [
                x.get(
                    "ec2_stress_network_latency_network_delay",
                    ec2_stress_network_latency_network_delay,
                )
            ],
        }
        for x in ec2_stress_network_latency_parameter_map
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not param_map:
        param_map["default"] = def_ssm_doc_params

    sum_duration = [int(param_map[x]["duration"][0]) for x in param_map]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="StressNetworkLatency",
        failure_mode=ParameterMapFailuremode[ec2_stress_network_latency_failure_mode],
        param_map=param_map,
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


def ec2_stress_network_utilization(
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    ec2_stress_network_utilization_port_type: str = "sport",
    ec2_stress_network_utilization_port_number: str = "0",
    ec2_stress_network_utilization_network_rate: str = "100",
    ec2_stress_network_utilization_duration: str = "60",
    ec2_stress_network_utilization_interface: str = "eth0",
    max_duration: str = "900",
    ec2_stress_network_utilization_parameter_map: dict[str, dict] = {},
    ec2_stress_network_utilization_failure_mode: str = "FailFast",
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
        "duration": [ec2_stress_network_utilization_duration],
        "interface": [ec2_stress_network_utilization_interface],
        "portType": [ec2_stress_network_utilization_port_type],
        "portNumber": [ec2_stress_network_utilization_port_number],
        "rate": [ec2_stress_network_utilization_network_rate],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not ec2_stress_network_utilization_parameter_map:
        ec2_stress_network_utilization_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(ec2_stress_network_utilization_parameter_map[x]["duration"][0])
        for x in ec2_stress_network_utilization_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="StressNetworkUtilization",
        failure_mode=ParameterMapFailuremode[
            ec2_stress_network_utilization_failure_mode
        ],
        param_map=ec2_stress_network_utilization_parameter_map,
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


def ec2_stress_cpu(
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    ec2_cpu_duration: str = "60",
    max_duration: str = "900",
    ec2_cpu_percent: str = "80",
    ec2_stress_cpu_parameter_map: dict[str, dict] = {},
    ec2_stress_cpu_failure_mode: str = "FailFast",
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
        "duration": [ec2_cpu_duration],
        "cpu": [ec2_cpu_percent],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not ec2_stress_cpu_parameter_map:
        ec2_stress_cpu_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(ec2_stress_cpu_parameter_map[x]["duration"][0])
        for x in ec2_stress_cpu_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="StressCPU",
        failure_mode=ParameterMapFailuremode[ec2_stress_cpu_failure_mode],
        param_map=ec2_stress_cpu_parameter_map,
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


def ec2_stress_memory(
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    ec2_stress_memory_duration: str = "60",
    max_duration: str = "900",
    ec2_stress_memory_percent_per_worker: str = "50",
    ec2_stress_memory_number_of_workers: str = "1",
    ec2_stress_memory_parameter_map: dict[str, dict] = {},
    ec2_stress_memory_failure_mode: str = "FailFast",
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
        "duration": [ec2_stress_memory_duration],
        "numberOfWorkers": [ec2_stress_memory_number_of_workers],
        "memoryPercentagePerWorker": [ec2_stress_memory_percent_per_worker],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not ec2_stress_memory_parameter_map:
        ec2_stress_memory_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(ec2_stress_memory_parameter_map[x]["duration"][0])
        for x in ec2_stress_memory_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="StressMemory",
        failure_mode=ParameterMapFailuremode[ec2_stress_memory_failure_mode],
        param_map=ec2_stress_memory_parameter_map,
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


def ec2_stress_cpu(
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    ec2_stress_cpu_duration: str = "60",
    max_duration: str = "900",
    stress_cpu_percent: str = "50",
    ec2_stress_cpu_parameter_map: dict[str, dict] = {},
    ec2_stress_cpu_failure_mode: str = "FailFast",
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
        "cpu": [stress_cpu_percent],
        "duration": [ec2_stress_cpu_duration],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not ec2_stress_cpu_parameter_map:
        ec2_stress_cpu_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(ec2_stress_cpu_parameter_map[x]["duration"][0])
        for x in ec2_stress_cpu_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="StressCPU",
        failure_mode=ParameterMapFailuremode[ec2_stress_cpu_failure_mode],
        param_map=ec2_stress_cpu_parameter_map,
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


def ec2_exhaust_root_vol(
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    ec2_exhaust_root_vol_duration: str = "60",
    max_duration: str = "900",
    ec2_exhaust_root_vol_parameter_map: dict[str, dict] = {},
    ec2_exhaust_root_vol_failure_mode: str = "FailFast",
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
        "duration": [ec2_exhaust_root_vol_duration],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not ec2_exhaust_root_vol_parameter_map:
        ec2_exhaust_root_vol_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(ec2_exhaust_root_vol_parameter_map[x]["duration"][0])
        for x in ec2_exhaust_root_vol_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="DiskVolumeExhaustion",
        failure_mode=ParameterMapFailuremode[ec2_exhaust_root_vol_failure_mode],
        param_map=ec2_exhaust_root_vol_parameter_map,
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


def ec2_blackhole_by_port(
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    ec2_blackhole_by_port_protocol: str = "tcp udp",
    ec2_blackhole_by_port_source_ports: str = "",
    ec2_blackhole_by_port_destination_ports: str = "",
    ec2_blackhole_by_port_direction: str = "BOTH",
    ec2_blackhole_by_port_duration: str = "60",
    max_duration: str = "900",
    ec2_blackhole_by_port_parameter_map: dict[str, dict] = {},
    ec2_blackhole_by_port_failure_mode: str = "FailFast",
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
        "duration": [ec2_blackhole_by_port_duration],
        "protocol": [ec2_blackhole_by_port_protocol],
        "sourcePorts": [ec2_blackhole_by_port_source_ports],
        "destinationPorts": [ec2_blackhole_by_port_destination_ports],
        "direction": [ec2_blackhole_by_port_direction],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not ec2_blackhole_by_port_parameter_map:
        ec2_blackhole_by_port_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(ec2_blackhole_by_port_parameter_map[x]["duration"][0])
        for x in ec2_blackhole_by_port_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="BlackholeByPort",
        failure_mode=ParameterMapFailuremode[ec2_blackhole_by_port_failure_mode],
        param_map=ec2_blackhole_by_port_parameter_map,
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


def ec2_blackhole_by_ip(
    ec2_blackhole_ip: str,
    targets: list[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
    ec2_blackhole_by_ip_port_protocol: str = "tcp udp",
    ec2_blackhole_by_ip_direction: str = "BOTH",
    ec2_blackhole_by_ip_duration: str = "60",
    max_duration: str = "900",
    ec2_blackhole_by_ip_parameter_map: dict[str, dict] = {},
    ec2_blackhole_by_ip_failure_mode: str = "FailFast",
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
        "duration": [ec2_blackhole_by_ip_duration],
        "protocol": [ec2_blackhole_by_ip_port_protocol],
        "sourceIP": [ec2_blackhole_ip],
        "destinationIP": [ec2_blackhole_ip],
        "direction": [ec2_blackhole_by_ip_direction],
    }

    def_instance_params = {
        "test_target_type": test_target_type,
        "tag_key": tag_key,
        "tag_value": tag_value,
        "instance_ids": test_instance_ids,
        "region": region,
    }
    if not ec2_blackhole_by_ip_parameter_map:
        ec2_blackhole_by_ip_parameter_map["default"] = def_ssm_doc_params

    sum_duration = [
        int(ec2_blackhole_by_ip_parameter_map[x]["duration"][0])
        for x in ec2_blackhole_by_ip_parameter_map
    ]
    if sum_duration[0] > int(max_duration):
        logger.error(
            f"{function_name}(): Combined duration over max: {sum_duration} > {max_duration}"
        )
        raise ActivityFailed(
            f"Combined duration over max: {sum_duration} > {max_duration}"
        )

    results = run_ssm_doc_multistage(
        doc_name="BlackholeByIP",
        failure_mode=ParameterMapFailuremode[ec2_blackhole_by_ip_failure_mode],
        param_map=ec2_blackhole_by_ip_parameter_map,
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


def remove_iam_role(
    region: str = "us-east-1",
    name_space: str = None,
    instance_tag_value: str = None,
    profile_tag_value: str = None,
    sleep_length: int = 10,
):
    command_execution_intance = get_test_instance_ids(
        test_target_type="RANDOM", tag_key="tag:Name", tag_value=instance_tag_value
    )

    instance_profile_name = get_instance_profile_name(
        tagKey="tag:Name", tagValue=profile_tag_value
    )
    role_name = get_role_from_instance_profile(instance_profile_name)

    print(f"IAM policy to remove IAM role from: {instance_profile_name}")
    print(f"IAM role to remove from Instance Profile: {role_name}")
    # print(f"Instance to remove IAM role from: {}")

    session = boto3.Session()
    b3 = session.client("iam", region)

    try:
        response = b3.remove_role_from_instance_profile(
            InstanceProfileName=instance_profile_name, RoleName=role_name
        )
        time.sleep(sleep_length)
        resp = b3.add_role_to_instance_profile(
            InstanceProfileName=instance_profile_name, RoleName=role_name
        )
    except ClientError as e:
        logger.error(e)
        raise

    return True


def terminate_instance(
    targets: List[str] = None,
    test_target_type: str = "RANDOM",
    tag_key: str = None,
    tag_value: str = None,
    region: str = "us-east-1",
):
    function_name = inspect.stack()[0][3]
    test_instance_ids = get_test_instance_ids(
        test_target_type=test_target_type,
        tag_key=tag_key,
        tag_value=tag_value,
        instance_ids=targets,
    )
    logger.info(function_name, "(): test_instance_ids= ", test_instance_ids)

    session = boto3.Session()
    ec2client = session.client("ec2", region)

    try:
        response = ec2client.terminate_instances(InstanceIds=test_instance_ids)
    except ClientError as e:
        logger.error(e)
        raise


if __name__ == "__main__":
    ec2_stress_network_latency(
        tag_key="tag:k8s.io/cluster-autoscaler/experiment-eks",
        tag_value="owned",
    )
    ec2_stress_packet_loss(
        tag_key="tag:k8s.io/cluster-autoscaler/experiment-eks",
        tag_value="owned",
        ec2_stress_packet_loss_parameter_map={
            "loss_20_percent": {"ec2_stress_packet_loss_percent": "20"},
            "loss_80_percent": {"ec2_stress_packet_loss_percent": "80"},
        },
    )
