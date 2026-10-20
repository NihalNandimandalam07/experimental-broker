import boto3

def get_ssm_parameter(parameter_path: str):
    ssm_client = boto3.client('ssm')

    try:
        response = ssm_client.get_parameter(Name=parameter_path)

        parameter_value = response['Parameter']['Value']
        return parameter_value

    except ssm_client.exceptions.ParameterNotFound:
        print(f"No parameter found at path: {parameter_path}")
        return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None