resource "aws_ecr_repository" "experiment_broker" {
  name = var.ecr_repository_name
}

resource "null_resource" "build_codebuild_image" {
  provisioner "local-exec" {
    interpreter = ["bash"]
    command = "ECR_REPOSITORY_URL='${aws_ecr_repository.experiment_broker.repository_url}' TF_VERSION='${var.terraform_version}' AWS_REGION='${data.aws_region.current.id}' AWS_ACCOUNT_ID='${data.aws_caller_identity.current.account_id}' ${path.module}/build_codebuild_image.sh"
  }

  triggers = {
    deployment = timestamp()
  }
  depends_on = [ aws_ecr_repository.experiment_broker]
}

# resource "docker_image" "pipeline_build" {
#   name = var.pipeline_build_docker_image_name
#   keep_locally = false
#   build {
#     args = {
#       TF_VERSION = "${var.terraform_version}"
#     }
#   }
#   # Trigger on any change to the dockerfile or tfvars files
#   triggers = {
#     sha1 = join("",[filesha1("./Dockerfile"),join("", [for f in fileset(path.module, "**.tfvars") : filesha1(f)])])
#   }
# }

