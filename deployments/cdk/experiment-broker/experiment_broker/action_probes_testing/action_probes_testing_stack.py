from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
    Duration,
    aws_ssm as ssm,
    aws_iam as _iam,
    aws_cognito as cognito,
    aws_s3 as s3,
    RemovalPolicy,
    aws_events as events,
    aws_ec2 as ec2, 
    aws_ecs as ecs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events_targets as targets,
    Tags,
)
from constructs import Construct

class ActionProbesTestingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        test_bucket = s3.Bucket(
            self,
            "TestBucket",
            bucket_name="ebap-test",
            removal_policy=RemovalPolicy.DESTROY,
        )

        begin_bucket = s3.Bucket(
            self,
            "BeginBucket",
            bucket_name="ebap-begin",
            removal_policy=RemovalPolicy.DESTROY,
            event_bridge_enabled=True
        )


        self.sfn_role = _iam.Role(
            self,
            "EBTestingStateMachine",
            assumed_by=_iam.ServicePrincipal("states.amazonaws.com"),
        )
        
        self.sfn_role.add_managed_policy(
            _iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaRole")
        )

        self.create_wait_machine_flow(name='Wait',simple_eval_lambda=True, bucket_name=begin_bucket.bucket_name)
        self.create_wait_machine_flow(name='Wait2')

    def create_wait_machine_flow(self, name:str, simple_eval_lambda:bool=False, bucket_name:str=''):

        wait = sfn.Wait(self, name, time=sfn.WaitTime.duration(Duration.minutes(1)))
        wait_machine = sfn.StateMachine(
            self,
            f"{name}Machine",
            definition_body=sfn.DefinitionBody.from_chainable(wait),
            role=self.sfn_role,
        )

        Tags.of(wait_machine).add("Type", "RegressionTesting")
        
        state_machine_arn_param = ssm.StringParameter(
            self, f"{name}MachineArnParameter",
            parameter_name=f"/RegressionTesting/StateMachineArns/{name}", 
            string_value=wait_machine.state_machine_arn
        )    

        if simple_eval_lambda:
            eval_lambda = _lambda.Function(
                self,
                f'{name}SFNTestLambda',
                runtime=_lambda.Runtime.PYTHON_3_10,
                code=_lambda.Code.from_asset('experiment_broker/action_probes_testing/lambda'),
                handler='main.lambda_handler',
                function_name=f'ebap-statemachine-test-{name}',
            )
            
            lambda_task = tasks.LambdaInvoke(
                self,
                f"{name}InvokeLambdaTask",
                lambda_function=eval_lambda,
                payload_response_only=True,
            )

            wait.next(lambda_task)

            eval_lambda.grant_invoke(wait_machine)        

        if bucket_name:

            events.Rule(self, f"{name}UploadRule",
                event_pattern=events.EventPattern(
                    source=["aws.s3"],
                    detail_type=["Object Created"],
                    detail={
                            "bucket": {
                                "name": [bucket_name]
                            }
                        }
                ),
                targets=[targets.SfnStateMachine(wait_machine)]
            )
