from handler import handler
from dataclasses import dataclass


@dataclass
class context:
    function_name: str = "test"
    aws_request_id: str = "88888888-4444-4444-4444-121212121212"
    invoked_function_arn: str = "arn:aws:lambda:eu-west-1:123456789101:function:test"


event_dict = {
    "experiment_source": "Demo-Kubernetes(EKS)-Worker Node (Pod)-State-TerminationCrash.yml",
    "bucket_name": "resiliencyvr-package-build-bucket-demo",
    "output_config": {
        "S3": {
            "bucket_name": "resiliencyvr-package-build-bucket-demo",
            "path": "experiment_journals",
        },
    },
}

handler(event=event_dict, context=context)
