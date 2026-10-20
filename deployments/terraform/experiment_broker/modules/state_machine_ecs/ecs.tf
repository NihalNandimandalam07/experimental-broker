resource "aws_ecs_cluster" "ecs_cluster" {
  name = "eb-test-ecs-cluster"
}

resource "aws_iam_role" "experiment_ecs_role" {
  name = "experiment-ecs-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

data "aws_iam_policy_document" "ecs_function_policy" {
  #SSM Permissions Statement
  statement {
    sid    = "ECSSSMPermissions"
    effect = "Allow"
    actions = [
      "ssm:SendCommand",
      "ssm:ListCommandInvocations"
    ]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "ssm:ResourceTag/${var.iam_tag_key}"
      values   = ["${var.iam_tag_value}"]
    }
  }

  #S3 Permissions Statement
  statement {
    sid    = "ECSS3Permissions"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject"
    ]
    resources = [
      "${aws_s3_bucket.experiments_bucket.arn}",
      "${aws_s3_bucket.experiments_bucket.arn}/*"
    ]

  }

  statement {
    sid    = "ECSNetworkPermissions"
    effect = "Allow"
    actions = [
      "ec2:DeleteRouteTable",
      "ec2:CreateRouteTable",
    ]
    resources = [
      "*"
    ]

    #Replace Value with proper VPC name
    condition {
      test     = "StringEquals"
      variable = "ec2:Vpc"
      values   = ["arn:aws:ec2:*:*:vpc-*"]

    }
  }

  statement {
    sid    = "ECSEC2Permissions"
    effect = "Allow"
    actions = [
      "ec2:DescribeSubnets",
      "ec2:DescribeAvailabilityZones",
      "ec2:DescribeVpcs",
      "ec2:DescribeNetworkAcls",
      "ec2:DescribeRouteTables",
      "ec2:CreateNetworkAcl",
      "ec2:CreateNetworkAclEntry",
      "ec2:CreateTags",
      "ec2:ReplaceNetwortAclAssociation",
      "ec2:DeleteNetworkAcl"
    ]
    resources = [
      "*"
    ]
  }

  statement {
    sid    = "LegacyPermissions"
    effect = "Allow"
    actions = [
      "ecs:List*",
      "ecs:Describe*",
      "ecs:StartTask",
      "ecs:RunTask",
      "ecs:StopTask",
      "ecs:ExecuteCommand",
      "ecs:DiscoverPollEndpoint",
      "ecs:PutAttributes",
      "ecs:UpdateTaskSet",
      "ec2:RunInstances",
      "ec2:TerminateInstances",
      "ec2:StopInstances",
      "ec2:StartInstances",
      "ec2:DescribeInstances",

    ]
    resources = [
      "*"
    ]
  }

  statement {
    sid    = "ContainerPermissions"
    effect = "Allow"
    actions = [
      "ecr:*",
      "states:SendTaskSuccess"

    ]
    resources = [
      "*"
    ]
  }

  statement {
    sid    = "LoggingPermissions"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"

    ]
    resources = ["arn:aws:logs:${data.aws_region.current_name}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/eb-test-payload-processor*"]
  }
}

resource "aws_iam_policy" "experiment_ecs_policy" {
  name   = "experiment_ecs_policy"
  policy = data.aws_iam_policy_document.ecs_function_policy.json
}

resource "aws_iam_role_policy_attachment" "experiment_ecs_policy_attach" {
  role       = aws_iam_role.experiment_ecs_role.name
  policy_arn = aws_iam_policy.experiment_ecs_policy.arn
}

resource "aws_ecr_repository" "payload_processor_repo" {
  name                 = "eb-test-payload-processor"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecs_task_definition" "payload_processor_task" {
  family       = "eb-test-payload-processor"
  network_mode = "awsvpc"
  cpu          = "256"
  memory       = "512"

  execution_role_arn = aws_iam_role.experiment_ecs_role.arn
  task_role_arn      = aws_iam_role.experiment_ecs_role.arn

  container_definitions = jsonencode([
    {
      name      = "payload-processor"
      image     = "${aws_ecr_repository.payload_processor_repo.repository_url}:latest"
      essential = true
      logconfiguration = {
        logdriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/eb-task-payload-processor"
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
        }
      }

      environment = [
        {
          "Name" : "task_token",
          "Value.$" : "$$.Task.Token"
        },
        {
          "Name" : "bucket_name",
          "Value.$" : "$.bucket_name"
        },
        {
          "Name" : "experiment_source",
          "Value.$" : "$.experiment_source"
        },
        {
          "Name" : "output_bucket",
          "Value.$" : "$.output_bucket"
        },
        {
          "Name" : "output_path",
          "Value.$" : "$.output_path"
        }
      ]

      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
          protocol      = "tcp"
        }
      ]
    }
  ])
}

resource "aws_ecs_service" "payload_processor_service" {
  name            = "eb-test-payload-processor-service"
  cluster         = aws_ecs_cluster.ecs_cluster.id
  task_definition = aws_ecs_task_definition.payload_processor_task.arn
  desired_count   = 0
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.ecs_subnet_ids
    security_groups  = [aws_security_group.ecs_security_group.id]
    assign_public_ip = true
  }
}

resource "aws_cloudwatch_log_group" "ecs_log_group" {
  name              = "/ecs/eb-test-payload-processor"
  retention_in_days = 7
}

resource "aws_security_group" "ecs_security_group" {
  name        = "experiment-ecs-sg"
  description = "Allow inbound and outbound traffic to ECS tasks"
  vpc_id      = var.ecs_vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "null_resource" "build_ecr_container" {
  provisioner "local-exec" {
    command = "${path.module}/build_to_ecr.sh"
  }

  triggers = {
    deployment = timestamp()
  }
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id             = var.ecs_vpc_id
  service_name       = "com.amazonaws.${data.aws_region.current.name}.ecr.dkr"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = var.ecs_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoint_sg.id]

  private_dns_enabled = true
  tags = {
    Name = "ecr-dkr-endpoint"
  }
}

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id             = var.ecs_vpc_id
  service_name       = "com.amazonaws.${data.aws_region.current.name}.ecr.api"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = var.ecs_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoint_sg.id]

  private_dns_enabled = true
  tags = {
    Name = "ecr-api-endpoint"
  }
}

resource "aws_vpc_endpoint" "logs" {
  vpc_id             = var.ecs_vpc_id
  service_name       = "com.amazonaws.${data.aws_region.current.name}.logs"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = var.ecs_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoint_sg.id]

  private_dns_enabled = true
  tags = {
    Name = "cloudwatch-logs-endpoint"
  }
}

resource "aws_vpc_endpoint" "ec2" {
  vpc_id             = var.ecs_vpc_id
  service_name       = "com.amazonaws.${data.aws_region.current.name}.ec2"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = var.ecs_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoint_sg.id]

  private_dns_enabled = true
  tags = {
    Name = "ec2-endpoint"
  }
}

resource "aws_vpc_endpoint" "states" {
  vpc_id             = var.ecs_vpc_id
  service_name       = "com.amazonaws.${data.aws_region.current.name}.states"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = var.ecs_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoint_sg.id]

  private_dns_enabled = true
  tags = {
    Name = "states-endpoint"
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = var.ecs_vpc_id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.ecs_route_table_ids

  tags = {
    Name = "s3-endpoint"
  }
}

resource "aws_security_group" "vpc_endpoint_sg" {
  name        = "vpc-endpoint-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = var.ecs_vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}