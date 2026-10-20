import time, os, json

import logging
import pytest
import boto3
from chaoslib.exceptions import ActivityFailed
from vr_regression_testing.general.actions import copy_object_s3, block_until_complete, initiate_next_sfn
from vr_regression_testing.general.probes import watch_sfn_execution, identify_sfn_execution


@pytest.fixture(scope="module")
def s3_client():
    return boto3.client('s3')

@pytest.fixture(scope="module")
def upload_txt_files(s3_client, s3_buckets):
    source_bucket, target_bucket = s3_buckets
    txt_files = ['pass.txt', 'fail_sfn_probe.txt']
    for file_name in txt_files:
        s3_client.put_object(Bucket=source_bucket, Key=file_name, Body=b'')
    return txt_files

@pytest.fixture(scope="module")
def s3_buckets():
    return 'ebap-test', 'ebap-begin'

# Test copy action

def test_copy_object_s3_pass(s3_buckets):
    source_bucket, target_bucket = s3_buckets
    assert copy_object_s3(source_bucket, 'pass.txt', target_bucket) is True

def test_copy_object_s3_fail(s3_buckets):
    source_bucket, target_bucket = s3_buckets    
    with pytest.raises(ActivityFailed):
        copy_object_s3(source_bucket, 'fail_copy_object.txt', target_bucket)

# Test block action
        
@pytest.mark.parametrize("watch_var, expected_result, retry_interval, max_retries", [
    ('EXECUTION_STATUS', 'SUCCEEDED', 1, 10),  # Successful case
    ('EXECUTION_STATUS', None, 1, 2),          # Retry limit case
])
def test_block_until_complete(watch_var, expected_result, retry_interval, max_retries):
    if expected_result:
        os.environ[watch_var] = expected_result

    if expected_result is None:
        with pytest.raises(ActivityFailed):
            block_until_complete(watch_var=watch_var, retry_interval=retry_interval, max_retries=max_retries)
    else:
        assert block_until_complete(watch_var=watch_var, retry_interval=retry_interval, max_retries=max_retries)

# Test sfn status probes

def test_watch_sfn_execution_no_arn():
    os.environ.pop('CURRENT_EXECUTION_ARN', None)
    assert watch_sfn_execution()

def test_watch_sfn_complete_success(s3_buckets, caplog):
    logging.info("Testing watch sfn success case\n")
    source_bucket, target_bucket = s3_buckets
    copy_object_s3(source_bucket, 'pass.txt', target_bucket)
    
    identify = identify_sfn_execution(retry_num=3, retry_interval=5)
    assert identify

    watch = watch_sfn_execution()
    assert watch
    assert "Evaluating execution" in caplog.text

def test_watch_sfn_execution_fail(s3_buckets, caplog):
    logging.info("Testing watch sfn fail case\n")
    source_bucket, target_bucket = s3_buckets
    copy_object_s3(source_bucket, 'fail_sfn_probe.txt', target_bucket)
    
    identify_sfn_execution(retry_num=3, retry_interval=5)

    watch = watch_sfn_execution()
    assert not watch and "Evaluating execution" in caplog.text

def test_identify_sfn_execution_with_no_job_id():
    os.environ.pop('JOB_ID', None)
    assert identify_sfn_execution(retry_num=3, retry_interval=5)

def test_identify_sfn_execution_timeout():
    os.environ['JOB_ID'] = "ABC"

    assert not identify_sfn_execution(retry_num=3, retry_interval=1)

def test_initiate_next_sfn_exception():
    next_sfn_param = "nonexistent_value"
    with pytest.raises(ActivityFailed):
        initiate_next_sfn(next_sfn_param)

def test_initiate_next_sfn_payload_pass():
    next_sfn_param = "Wait2"
    
    os.environ.pop("CURRENT_SFN_ARN", None)
    os.environ.pop("CURRENT_EXECUTION_ARN", None)

    initiate_next_sfn(next_sfn_param)
    assert "CURRENT_SFN_ARN" in os.environ
    assert "CURRENT_EXECUTION_ARN" in os.environ

