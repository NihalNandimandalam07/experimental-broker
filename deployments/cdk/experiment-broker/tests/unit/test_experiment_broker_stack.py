import aws_cdk as core
import aws_cdk.assertions as assertions

from experiment_broker.experiment_broker_stack import ExperimentBrokerStack

# example tests. To run these tests, uncomment this file along with the example
# resource in experiment_broker/experiment_broker_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ExperimentBrokerStack(app, "experiment-broker")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
