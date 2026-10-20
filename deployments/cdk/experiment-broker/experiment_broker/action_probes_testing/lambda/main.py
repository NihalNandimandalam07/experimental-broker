def lambda_handler(event, context):
    print(event)
    object_key = event['detail']['object']['key']
    
    print("Object Key:", object_key)
    
    if 'fail' in object_key:
        raise Exception(f"Failure condition met for {object_key}")
    else:
        return {
            'statusCode': 200,
            'body': 'Success'
        }
