import logging, json, urllib3, os, boto3
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def authenticate():
    sm = boto3.client('secretsmanager')
    get_secret = sm.get_secret_value(
        SecretId='exp-broker-jira-auth'
    )
    secret = get_secret['SecretString'].split(':')
    
    http = urllib3.PoolManager()
    
    #authenticate
    authCred = '{"client_id":"' + secret[0] + '","client_secret":"' + secret[1] + '"}'
    auth_url = "https://xray.cloud.getxray.app/api/v2/authenticate"
    auth_response = http.request('POST', auth_url, body=authCred, headers={'Content-Type':'application/json'}, retries=False)
    xray_key = auth_response.data.decode("utf-8")
    auth_token = xray_key.strip('"')
    
    return auth_token

def create_new_execution(jira_ticket_id, auth_token):
    logger.info(f"received jira ticket: {jira_ticket_id}")
    
    http = urllib3.PoolManager()

    payload = {
        "info":{
            "project":"XI",
            "summary":f"Test Execution of {jira_ticket_id}"
        },
        "tests" : [{
            "testKey": jira_ticket_id,
            "status": "EXECUTING"
        }]
    }
    
    logger.info(payload)

    url= "https://xray.cloud.getxray.app/api/v2/import/execution"
    headers={"Authorization":f"Bearer {auth_token}", "Content-Type":"application/json"}
    response = http.request('POST', url=url, body=json.dumps(payload), headers=headers)
    res = json.loads(response.data.decode())
    logger.info(res)

    return res['key']