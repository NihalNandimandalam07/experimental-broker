# SSM Documents
This module creates SSM documents for the experiment broker.

To add an SSM document and make it available in Experiment Broker, you need to create a new file in the `ssm_documents` directory. The file should be named after the document name and have the `.yml` extension. The content of the file should be the yaml representation of the SSM document.

To deploy the document, create a terraform resource in ssm.tf, following the examples within.