import datetime as dt
from datetime import date, datetime

import boto3
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

PASS_PARAM = "query_token"
USERNAME = "query_username"


def get_pass_or_fail(response, missed_percent):
    data = response.json().get("body", {}).get("msg", {})[0]
    data_list = data.get("data").split("\n")
    data_keys = data_list[0].split("\t")
    data_values = data_list[1].split("\t")
    data_dict = dict(zip(data_keys, data_values))

    try:
        print(f'{data_dict.get("missed_sla_percent")} of transactions missed SLA')
        if missed_percent > float(data_dict.get("missed_sla_percent")):
            print(f"Transactions that missed SLA are under {missed_percent}%")
            print("Test has passed")
            return True
        else:
            print(f"Transactions that missed SLA are over {missed_percent}%")
            print("Test has failed")
            return False
    except ValueError:
        print("No test metadata exists")
        print("ERROR: Test time range is not valid")
        return False


def get_relative_time(minutes):
    now = datetime.now()
    testend = datetime.strptime(str(now), "%Y-%m-%d %H:%M:%S.%f")
    delta = dt.timedelta(minutes=minutes)
    teststart = testend - delta

    return str(teststart), str(testend)


def get_session():
    client = boto3.client("ssm")
    password = (
        client.get_parameter(Name=PASS_PARAM, WithDecryption=True)
        .get("Parameter")
        .get("Value")
    )

    session = requests.Session()
    session.post(
        "https://query-url",
        data={"userName": USERNAME, "password": password},
        verify=False,
    )

    return session


def load_probe_absolute(
    testday: str, teststart: str, testend: str, sla: str, missed_percent: int
) -> bool:
    """Queries DB to confirm missed SLA using timestamps"""

    session = get_session()

    run_table_create(session, testday)

    response = run_stats_collect(session, sla, teststart, testend)

    get_pass_or_fail(response, missed_percent)


def load_probe_relative(
    testday: str, minutes: int, sla: str, missed_percent: int
) -> bool:
    """Queries transaction DB to confirm missed SLA. Reports data from the past given number of minutes until the current time."""

    session = get_session()

    run_table_create(session, testday)

    teststart, testend = get_relative_time(minutes)
    response = run_stats_collect(session, sla, teststart, testend)

    get_pass_or_fail(response, missed_percent)


def run_table_create(session, testday):
    session.post(
        "https://query-url",
        json={"name": "create-database", "params": {"testday": testday}},
    )


def run_stats_collect(session, sla, teststart, testend):
    response = session.post(
        "https://query-url",
        json={
            "name": "get-stats",
            "params": {"sla": sla, "teststart": teststart, "testend": testend},
        },
    )
    return response
