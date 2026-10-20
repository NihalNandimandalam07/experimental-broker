# S3 Experiments Upload
This module creates an S3 bucket for uploading experiments to. All files under the `experiments` directory will be uploaded to this bucket.

## Sections
- [Creating an Experiment](#creating-an-experiment)
- [Uploading an Experiment](#uploading-an-experiment)

## Creating an Experiment
An **experiment** is a .yml or .yaml file containing an experiment configuration. It is composed of a steady state hypothesis, the experiment method, and optionally rollback.

See the [experiments directory](experiments) for examples of experiments.

## Uploading an Experiment
To upload an experiment to the S3 bucket, follow the steps outlined for [deploying Experiment Broker](/deployments/terraform/README.md), depending on if you have deployed from your manual machine or through CodePipeline.
