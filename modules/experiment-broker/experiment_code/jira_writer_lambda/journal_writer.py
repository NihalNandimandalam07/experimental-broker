import logging, json, urllib3, os, boto3
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(event)
    rec = event['Records']
    
    bucket_name = rec[0]['s3']['bucket']['name']
    key = rec[0]['s3']['object']['key']
    
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket_name, Key=key)
    file_content = obj["Body"].read()
    f = json.loads(file_content.decode('utf-8'))
    
    exp = f['experiment']
    logger.info(f)

    steps = []
    for step in f['run']:
        step_ = {
            "name":step["activity"]["name"],
            "status":"PASSED" 
        }
        steps.append(step_)
        
    exec_key = "XI-36" if not "jira_exec_ticket" in f.keys() else f["jira_exec_ticket"]
    test_ticket = "XI-32" if not "jira_test_ticket" in f.keys() else f["jira_test_ticket"] 
        
    test_results = {
        "testExecutionKey":exec_key,
        "info" : {
            "summary" : exp['title'],
            # "description" : exp['description'],
            "startDate" : f['start'].split(".")[0] + "+01:00",
            "finishDate" : f['end'].split(".")[0] + "+01:00"
        },
        "tests" : [{
            "testKey": test_ticket,
            "start":f['start'].split(".")[0] + "+01:00",
            "finish":f['end'].split(".")[0] + "+01:00",
            "status":"PASSED" if f['status'] == 'completed' else "FAILED",
            "evidences":[
                {
                    "data": base64.b64encode(file_content).decode('utf-8'),
                    "filename":key,
                    "contentType":"text/plain"
                }
            ]
            # ,
            # "iterations":[
            #     {
            #         "steps":steps
            #     }
            # ]
        }]
    }
    post_body = json.dumps(test_results)
    

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


    url= "https://xray.cloud.getxray.app/api/v2/import/execution"
    headers={"Authorization":f"Bearer {auth_token}", "Content-Type":"application/json"}
    response = http.request('POST', url=url, body=post_body, headers=headers)
    logger.info(response.status)
    logger.info(response.data)
    

    return {
        'statusCode':response.status,
        'body':response.data
    }