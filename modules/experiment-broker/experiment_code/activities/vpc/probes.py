import boto3
import json
from shared import (
    get_subnets_by_vpc_id,
    get_subnets_by_az_id,
    get_subnets_by_subnet_ids,
    assert_subnet_nacl_association_by_tag,
    assert_subnet_nacl_association_by_nacl,
)
from chaoslib import ActivityFailed
from activities.state import load_rollback_config


def assert_nacl_failure_by_subnet(
    subnet_id, region, failure_nacl_tag_key, failure_nacl_tag_value
):
    results = {}

    try:
        subnet_nacl_association_response = assert_subnet_nacl_association_by_tag(
            subnet_id, region, failure_nacl_tag_key, failure_nacl_tag_value
        )
    except AssertionError as e:
        if str(e) == "NO NACL MATCH":
            results[subnet_id] = (
                f"NACL tags do not contain a match. Expected Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
            )
        if str(e) == "NO TAGS":
            results[subnet_id] = (
                f"The NACL does not have any Tags. Expected Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
            )
        if str(e) == "NO NACLS":
            results[subnet_id] = (
                f"No Nacls are associated with the provided subnet_id. Expected a NACL with Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
            )

    if results:
        result_message = json.dumps(results)
        raise ActivityFailed(
            f"NACL tags do not contain a match for subnet_id(s). {result_message}"
        )
    else:
        return True


def assert_nacl_rollback_by_subnet(state_file_name, configuration, subnet_id, region):
    if rollback_config := load_rollback_config(
        filename=state_file_name, configuration=configuration
    ):
        results = {}
        if (
            subnet_id
            in rollback_config["subnet_association_id_old_nacl_id_pairs"].keys()
        ):
            nacl_id = rollback_config["subnet_association_id_old_nacl_id_pairs"][
                subnet_id
            ]
            try:
                subnet_nacl_association_response = (
                    assert_subnet_nacl_association_by_nacl(
                        subnet_id=subnet_id,
                        nacl_id=nacl_id,
                        region=region,
                    )
                )
            except AssertionError as e:
                raise ActivityFailed(
                    f"ASSERTIONERROR: Expected NACL not found for subnet pairing {subnet_id} : {nacl_id} {e}"
                )
        return True


def assert_nacl_failure_by_vpc(
    vpc_id, region, failure_nacl_tag_key, failure_nacl_tag_value
):
    subnet_ids = get_subnets_by_vpc_id()

    results = {}
    for subnet_id in subnet_ids:
        try:
            subnet_nacl_association_response = assert_subnet_nacl_association_by_tag(
                subnet_id, region, failure_nacl_tag_key, failure_nacl_tag_value
            )
        except AssertionError as e:
            if str(e) == "NO NACL MATCH":
                results[subnet_id] = (
                    f"NACL tags do not contain a match. Expected Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
            if str(e) == "NO TAGS":
                results[subnet_id] = (
                    f"The NACL does not have any Tags. Expected Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
            if str(e) == "NO NACLS":
                results[subnet_id] = (
                    f"No Nacls are associated with the provided subnet_id. Expected a NACL with Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
    if results:
        result_message = json.dumps(results)
        raise ActivityFailed(
            f"NACL tags do not contain a match for subnet_id(s). {result_message}"
        )
    else:
        return True

def assert_nacl_rollback_by_vpc(
    vpc_id, region, failure_nacl_tag_key, failure_nacl_tag_value
):
    subnet_ids = get_subnets_by_vpc_id()
    return


def assert_nacl_failure_by_az(
    az_id, region, failure_nacl_tag_key, failure_nacl_tag_value
):

    subnet_ids = get_subnets_by_az_id(az_id=az_id, region=region)

    results = {}
    for subnet_id in subnet_ids:
        try:
            subnet_nacl_association_response = assert_subnet_nacl_association_by_tag(
                subnet_id, region, failure_nacl_tag_key, failure_nacl_tag_value
            )
        except AssertionError as e:
            if str(e) == "NO NACL MATCH":
                results[subnet_id] = (
                    f"NACL tags do not contain a match. Expected Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
            if str(e) == "NO TAGS":
                results[subnet_id] = (
                    f"The NACL does not have any Tags. Expected Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
            if str(e) == "NO NACLS":
                results[subnet_id] = (
                    f"No Nacls are associated with the provided subnet_id. Expected a NACL with Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
    if results:
        result_message = json.dumps(results)
        raise ActivityFailed(
            f"NACL tags do not contain a match for subnet_id(s). {result_message}"
        )
    else:
        return True


def assert_nacl_rollback_by_az(
    az_id, region, failure_nacl_tag_key, failure_nacl_tag_value
):
    vpc_client = boto3.client(region)

    return


def assert_route_table_subnet_associations_by_route_table(
    subnet_ids, region, failure_nacl_tag_key, failure_nacl_tag_value
):
    results = {}
    for subnet_id in subnet_ids:
        try:
            subnet_nacl_association_response = assert_subnet_nacl_association_by_tag(
                subnet_id, region, failure_nacl_tag_key, failure_nacl_tag_value
            )
        except AssertionError as e:
            if str(e) == "NO NACL MATCH":
                results[subnet_id] = (
                    f"NACL tags do not contain a match. Expected Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
            if str(e) == "NO TAGS":
                results[subnet_id] = (
                    f"The NACL does not have any Tags. Expected Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
            if str(e) == "NO NACLS":
                results[subnet_id] = (
                    f"No Nacls are associated with the provided subnet_id. Expected a NACL with Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
    if results:
        result_message = json.dumps(results)
        raise ActivityFailed(
            f"NACL tags do not contain a match for subnet_id(s). {result_message}"
        )
    else:
        return True


def assert_route_table_subnet_associations_by_vpc(
    subnet_ids, region, failure_nacl_tag_key, failure_nacl_tag_value
):
    results = {}
    for subnet_id in subnet_ids:
        try:
            subnet_nacl_association_response = assert_subnet_nacl_association_by_tag(
                subnet_id, region, failure_nacl_tag_key, failure_nacl_tag_value
            )
        except AssertionError as e:
            if str(e) == "NO NACL MATCH":
                results[subnet_id] = (
                    f"NACL tags do not contain a match. Expected Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
            if str(e) == "NO TAGS":
                results[subnet_id] = (
                    f"The NACL does not have any Tags. Expected Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
            if str(e) == "NO NACLS":
                results[subnet_id] = (
                    f"No Nacls are associated with the provided subnet_id. Expected a NACL with Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
    if results:
        result_message = json.dumps(results)
        raise ActivityFailed(
            f"NACL tags do not contain a match for subnet_id(s). {result_message}"
        )
    else:
        return True


def assert_route_table_subnet_associations_by_az(
    subnet_ids, region, failure_nacl_tag_key, failure_nacl_tag_value
):
    results = {}
    for subnet_id in subnet_ids:
        try:
            subnet_nacl_association_response = assert_subnet_nacl_association_by_tag(
                subnet_id, region, failure_nacl_tag_key, failure_nacl_tag_value
            )
        except AssertionError as e:
            if str(e) == "NO NACL MATCH":
                results[subnet_id] = (
                    f"NACL tags do not contain a match. Expected Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
            if str(e) == "NO TAGS":
                results[subnet_id] = (
                    f"The NACL does not have any Tags. Expected Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
            if str(e) == "NO NACLS":
                results[subnet_id] = (
                    f"No Nacls are associated with the provided subnet_id. Expected a NACL with Tag with Key : {failure_nacl_tag_key} with Value : {failure_nacl_tag_value}"
                )
    if results:
        result_message = json.dumps(results)
        raise ActivityFailed(
            f"NACL tags do not contain a match for subnet_id(s). {result_message}"
        )
    else:
        return True
