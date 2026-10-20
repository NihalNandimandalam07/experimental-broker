import os
import yaml
import json

from aws_cdk import (
    Duration,
    Stack,
    aws_s3_deployment,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_kms as kms,
    aws_iam as iam,
    Aws,

    aws_s3_notifications as s3n,


    aws_ssm as ssm,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_logs as logs,
 
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_lambda as functions,
    RemovalPolicy,
)
from constructs import Construct

class ExperimentBrokerStack(Stack):
    path_to_ssm_files = "../../terraform/lambda_infra/ssm"
    name_prefix = "eb-test"
    sample_experiment_path = "../../Experiment-Broker-Module/experiment_code/tests/example_experiments"
    experiment_prefix = "experiments/"
    result_prefix = "journals/"
    trigger_lambda_code = "../../Experiment-Broker-Module/experiment_code/trigger_lambda/"
    ap_testing_bucket_arns = [
                "arn:aws:s3:::ebap-begin",
                "arn:aws:s3:::ebap-begin/*",
                "arn:aws:s3:::ebap-test",
                "arn:aws:s3:::ebap-test/*"
            ]

    journal_writer_lambda_code = "../../Experiment-Broker-Module/experiment_code/jira_writer_lambda/"
    xray_api_key_secret_id = "exp-broker-jira-auth"

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.service_role = iam.Role(self,
                                f"{self.name_prefix}-service-role",
                                assumed_by = iam.ServicePrincipal("ecs-tasks.amazonaws.com") )
        self.lambda_service_role = iam.Role(self,
                                            f"{self. name_prefix}-lambda-role",
                                            assumed_by = iam.ServicePrincipal("lambda.amazonaws.com"))
        kms_key = kms.Key(self, f"{self.name_prefix}-key")
        self.source_bucket = s3.Bucket(self,
                                    f"{self.name_prefix}-source-bucket",
                                    bucket_name = f"{self.name_prefix}-source",
                                    block_public_access = s3.BlockPublicAccess.BLOCK_ALL,
                                    auto_delete_objects = True,
                                    encryption_key = kms_key,
                                    enforce_ssl = True,
                                    removal_policy =  RemovalPolicy.DESTROY)
        test_experiments = self.add_test_experiments(self.source_bucket)
        self.service_role.add_to_policy(
                                iam.PolicyStatement(effect = iam.Effect.ALLOW,
                                                    actions = ["s3:PutObject",
                                                               "s3:GetObject",
                                                               "s3:ListObjects"],
                                                    resources = [self.source_bucket.bucket_arn,
                                                                self.source_bucket.bucket_arn + "/*",]+self.ap_testing_bucket_arns))
        self.service_role.add_to_policy(
                                    iam.PolicyStatement(effect = iam.Effect.ALLOW,
                                                        actions = ["kms:GenerateDataKey",
                                                                    "kms:Encrypt",
                                                                    "kms:Decrypt"],
                                                        resources = [kms_key.key_arn]
                                        ))
        self.service_role.add_to_policy(
                                    iam.PolicyStatement(effect = iam.Effect.ALLOW,
                                                        actions = ["eks:*"],
                                                        resources = ["*"])
        )
        self.service_role.add_to_policy(
                                    iam.PolicyStatement(effect = iam.Effect.ALLOW,
                                                        actions = ["ec2:DescribeInstances",
                                                                    "ec2:RunInstances",
                                                                    "ec2:TerminateInstances",
                                                                    "ec2:StopInstances",
                                                                    "ec2:StartInstances"],
                                                        resources = ["*"],
                                                        conditions = {"StringEquals":{"ec2:ResourceTag/Type": "Resiliency"} }))

        self.service_role.add_to_policy(
                            iam.PolicyStatement(effect = iam.Effect.ALLOW,
                                                        actions =   ["states:ListStateMachines",
                                                                "states:ListActivities",
                                                                "states:DescribeStateMachine",
                                                                "states:DescribeActivity",
                                                                "states:ListExecutions",
                                                                "states:DescribeExecution",
                                                                "states:GetExecutionHistory",
                                                                "states:StartExecution"],

                                                        resources = ["*"],
                                                        conditions = {"StringEquals":{"aws:ResourceTag/Type": "RegressionTesting"} }))

        self.service_role.add_to_policy(
                            iam.PolicyStatement(
                            actions=["ssm:GetParameter*", "ssm:GetParameters*", "ssm:GetParametersByPath*"],
                            resources=[f"arn:aws:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/RegressionTesting*"],
                            effect=iam.Effect.ALLOW
                        )
        )

        testing_vpc = ec2.Vpc(self,
                                f"{self.name_prefix}-Vpc",
                                vpc_name = f"{self.name_prefix}-vpc",
                                ip_addresses = ec2.IpAddresses.cidr("42.0.0.0/16"))
        self.ecs_cluster = ecs.Cluster(self,
                                    f"{self.name_prefix}-ecs-cluster",
                                    vpc = testing_vpc,
                                    enable_fargate_capacity_providers = True)
        self.ecs_cluster.apply_removal_policy(RemovalPolicy.DESTROY)

        map_path = sfn.Map(self, "Experiment_Broker_Loop",
                           state_name = "Experiment Loop",
                           max_concurrency = 1,
                           items_path = sfn.JsonPath.string_at("$.Payload.list"))

        processor_task = self.payload_processing_task()
        processor_path = processor_task.next(self.post_processing_choice(processor_task))
        map_path_definition = map_path.item_processor(processor_path)
        definition = self.first_choice(run_path = map_path_definition)
        state_machine  =  sfn.StateMachine(self, f"{self.name_prefix}_State_Machine",
                                            definition_body = sfn.DefinitionBody.from_chainable(definition),
                                            state_machine_name = f"{self.name_prefix}-State_Machine")


        self.service_role.add_to_policy(
            iam.PolicyStatement(effect = iam.Effect.ALLOW,
                                actions = ["states:SendTaskSuccess"],
                                resources = [state_machine.state_machine_arn]
                ))


        self.lambda_service_role.add_to_policy(
            iam.PolicyStatement(effect = iam.Effect.ALLOW,
                                actions = ["states:StartExecution",
                                            "states:SendTaskSuccess",
                                           "states:DescribeStateMachine"],
                                resources = [state_machine.state_machine_arn]
                ))
        self.onboard_ssm_documents()


        print(os.path.isdir(self.trigger_lambda_code))
        print(os.listdir(self.trigger_lambda_code))
        functions.Function(self, 
                            f"{self.name_prefix}-trigger",
                            function_name = f"{self.name_prefix}-trigger",
                            code = functions.Code.from_asset(self.trigger_lambda_code),
                            handler = "index.lambda_handler",
                            runtime=functions.Runtime.PYTHON_3_12,
                            timeout=Duration.seconds(120),
                            role = self.lambda_service_role,
                            environment = {
                                "STATE_MACHINE_ARN": state_machine.state_machine_arn,
                                "BUCKET_NAME": self.source_bucket.bucket_name,
                                "EXPERIMENT_PREFIX" : self.experiment_prefix,
                                "RESULT_PREFIX" : self.result_prefix
                            })

        
        jira_writer_lambda = functions.Function(self, 
                                                f"{self.name_prefix}-jira-writer",
                                                function_name = f"{self.name_prefix}-jira-writer",
                                                code = functions.Code.from_asset(self.journal_writer_lambda_code),
                                                handler = "journal_writer.handler",
                                                environment={'secret_id':self.xray_api_key_secret_id},
                                                timeout=Duration.seconds(60),
                                                role = self.lambda_service_role,
                                                runtime=functions.Runtime.PYTHON_3_10
                                            )
        
        jira_writer_lambda.role.attach_inline_policy(iam.Policy(self, 'xray-integration-policy',
                                                                statements=[
                                                                    iam.PolicyStatement(
                                                                        actions=['secretsmanager:GetSecretValue'],
                                                                        resources=[f'arn:aws:secretsmanager:*:*:secret:{self.xray_api_key_secret_id}*']
                                                                    ),
                                                                    iam.PolicyStatement(
                                                                        actions=['s3:GetObject'],
                                                                        resources=[f"{self.source_bucket.bucket_arn}/{self.result_prefix}*"]
                                                                    ),
                                                                    iam.PolicyStatement(
                                                                        actions = ["kms:GenerateDataKey","kms:Encrypt","kms:Decrypt"],
                                                                        resources = [kms_key.key_arn]
                                                                    )
                                                                ]))

        self.source_bucket.add_event_notification(s3.EventType.OBJECT_CREATED, 
                                                  s3n.LambdaDestination(jira_writer_lambda),
                                                  s3.NotificationKeyFilter(prefix=self.result_prefix)
                                                  )



    def onboard_ssm_document(self, document_path):
        with open(document_path, "r") as f:
            if document_path.split(".")[-1].lower() in set(["yml", "yaml"]):
                filename = os.path.splitext(os.path.basename(document_path))[0]
                document = ssm.CfnDocument(self, f"{self.name_prefix}-{filename}",
                                           content = yaml.safe_load(f.read()),
                                            name = f"{self.name_prefix}-{filename}",
                                            document_format = "YAML", #YAML | JSON | TEXT
                                            document_type = "Command") # ApplicationConfiguration | ApplicationConfigurationSchema | Automation | Automation.ChangeTemplate | ChangeCalendar | CloudFormation | Command | DeploymentStrategy | Package | Policy | ProblemAnalysis | ProblemAnalysisTemplate | Session
        return document

    def onboard_ssm_documents(self):
        for root, dirs, files in os.walk(self.path_to_ssm_files, topdown=True):
            print(f" root :{root}, dirs: {dirs}, files: {files}\n")
            for file in files:
                self.onboard_ssm_document(os.path.join(root, file))
        self.service_role.add_to_policy( iam.PolicyStatement(effect = iam.Effect.ALLOW,
                                                    actions = ["ssm:SendCommand",
                                                               "ssm:ListCommandInvocations"],
                                                    resources = [f"arn:aws:ssm:*:*:document/{self.name_prefix}-*"]))

    def add_test_experiments(self, bucket):
        #files_to_deploy = []
        #for root, _, files in os.walk(self.sample_experiment_path):
        #    for f in files:
        #        files_to_deploy.append((os.path.join(root, f)))
        deployment = aws_s3_deployment.BucketDeployment(self, "ExperimentTestFileDeployment",
                                                        sources = [aws_s3_deployment.Source.asset(self.sample_experiment_path)],
                                                        destination_bucket = bucket,
                                                        destination_key_prefix = self.experiment_prefix,
                                                        content_type = "text/plain")
        return deployment

    def first_choice(self, run_path):
        finish = sfn.Pass(self, "ExitState", state_name = "Exit")
        choice_run_eb = sfn.Choice(self, "run_app_tests_choice", state_name = "Run_Tests")
        finish_eb_condition = sfn.Condition.string_equals("$.Payload.state", "done")
        run_eb_condition = sfn.Condition.string_equals("$.Payload.state", "pending")
        return choice_run_eb.\
                    when(run_eb_condition, run_path).\
                    when(finish_eb_condition, finish)

    def post_processing_choice(self, processor_task):
        choice = sfn.Choice(self, "post-processor", state_name = "Post Process")
        condition_completed = sfn.Condition.string_equals("$.Payload.state", "done")
        condition_pending = sfn.Condition.string_equals("$.Payload.state", "pending")
        wait_and_retry = sfn.Wait(self, "wait_and_retry",
                                  time = sfn.WaitTime.duration(Duration.seconds(15)),
                                  comment = "wait and retry for processor task",
                                  state_name = "Wait & Retry").next(processor_task)
        completed = sfn.Pass(self, "ProcessorCompleted", state_name = "Complete")
        return choice.when(condition_completed, completed).when(condition_pending, wait_and_retry)

    def payload_processing_task(self):
        repo = self.provision_ecr_repository(id = "payload-processor")
        self.service_role.add_to_policy(
                            iam.PolicyStatement(effect = iam.Effect.ALLOW,
                                                actions = ["ecr:*"],
                                                resources = ["*"]))
        task_dict = self.provision_task_definition(id = "payload-processor",
                                                    service_role = self.service_role,
                                                    ecr_repository = repo)
        return tasks.EcsRunTask(self,
                f"{self.name_prefix}-run-payload-processor",
                integration_pattern=sfn.IntegrationPattern.RUN_JOB,
                cluster = self.ecs_cluster,
                launch_target = tasks.EcsFargateLaunchTarget(platform_version=ecs.FargatePlatformVersion.LATEST),
                task_definition = task_dict["task"],
                result_path = "$.Payload",
                state_name = "Process Payload",
                # commented out subnet because it can't pull from ECR for some reason
                #subnets = ec2.SubnetSelection(subnets = [self.provisioned_resources["public_subnet_selection"].subnets[0]]),
                container_overrides = [\
                        tasks.ContainerOverride(container_definition=task_dict["container"],
                                                    environment=[
                                                                tasks.TaskEnvironmentVariable(name="task_token",
                                                                                                value=sfn.JsonPath.task_token),
                                                                tasks.TaskEnvironmentVariable(name="bucket_name",
                                                                                                value=sfn.JsonPath.string_at("$.bucket_name")),
                                                                tasks.TaskEnvironmentVariable(name="experiment_source",
                                                                                                value=sfn.JsonPath.string_at("$.experiment_source")),
                                                                tasks.TaskEnvironmentVariable(name="output_bucket",
                                                                                                value=sfn.JsonPath.string_at("$.output_config.S3.bucket_name")),
                                                                tasks.TaskEnvironmentVariable(name="jira_exec_ticket",
                                                                                              value=sfn.JsonPath.string_at("$.jira_exec_ticket")),
                                                                tasks.TaskEnvironmentVariable(name="jira_test_ticket",
                                                                                                value=sfn.JsonPath.string_at("$.jira_test_ticket")),                                
                                                                tasks.TaskEnvironmentVariable(name="output_path",
                                                                                                value=sfn.JsonPath.string_at("$.output_config.S3.path"))]
                                                )]).add_catch(sfn.Fail(self, f"{self.name_prefix}-processing-failed", state_name = "Processing Failed"))

    def provision_ecr_repository(self, id):
        return ecr.Repository(self,
                                f"{self. name_prefix}-id",
                                repository_name = f"{self.name_prefix}-{id}",
                                image_scan_on_push = True,
                                removal_policy=RemovalPolicy.DESTROY,
                                empty_on_delete=True,
                                encryption = ecr.RepositoryEncryption.AES_256)

    def provision_task_definition(self,
                                    id,
                                    service_role,
                                    ecr_repository,
                                    image_tag_to_use = ":latest",
                                    cpu = 256,
                                    memory_limit = 512,
                                    port_mappings = None):
        task_definition = ecs.FargateTaskDefinition(self,
                                                        f"{self.name_prefix}-{id}",
                                                        execution_role = service_role,
                                                        task_role = service_role,
                                                        cpu = cpu,
                                                        memory_limit_mib = memory_limit)
        log_group = logs.LogGroup(self,
                                    f"{self.name_prefix}-{id}-log-group",
                                    log_group_name = f"ecs/{self.name_prefix}/{id}",
                                    removal_policy=RemovalPolicy.DESTROY,
                                    )
        log_driver = ecs.AwsLogDriver(
            log_group= log_group,
            stream_prefix= f'ART-{id}',
            mode= ecs.AwsLogDriverMode.NON_BLOCKING
        )
        if type(ecr_repository) is str:
            container_definition = task_definition.\
                                    add_container(ecr_repository.replace("/","-"),
                                    image = ecs.ContainerImage.from_registry(\
                                            ecr_repository + image_tag_to_use),
                                    logging = log_driver)
        else:
            container_definition = task_definition.\
                                    add_container(ecr_repository.repository_name,
                                    image = ecs.ContainerImage.from_registry(\
                                            ecr_repository.repository_uri + image_tag_to_use),
                                    logging = log_driver)
        if port_mappings:
            container_definition.add_port_mappings(ecs.PortMapping(**port_mappings))
        return {"task" :task_definition,"container": container_definition}


