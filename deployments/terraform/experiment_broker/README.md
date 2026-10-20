# Experiment Broker Infrastructure
This directory contains the Terraform code for deploying the Experiment Broker infrastructure.

# Modules
- kms_key
- [s3_experiments_upload](modules/s3_experiments_upload/README.md)
- [ssm_documents](modules/ssm_documents/README.md)
- state_machine_ecs
- [state_machine_lambda](modules/state_machine_lambda/README.md)