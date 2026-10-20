FROM public.ecr.aws/codebuild/standard:5.0

RUN curl -s -o terraform.zip https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip
RUN unzip terraform.zip
RUN chmod +x terraform
RUN mv terraform /usr/local/bin/

# RUN curl -s -o terragrunt https://github.com/gruntwork-io/terragrunt/releases/download/${TERRAGRUNT_VERSION}/terragrunt_linux_amd4
# RUN chmod +x terragrunt
# RUN mv terragrunt /usr/local/bin/