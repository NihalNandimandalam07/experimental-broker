resource "aws_codepipeline" "lambda_build" {
  name     = var.build_pipeline_name
  role_arn = aws_iam_role.codepipeline_role.arn

  pipeline_type = "V2"

  artifact_store {
    location = aws_s3_bucket.codepipeline_artifact_bucket.bucket
    type     = "S3"
  }

  # S3 Source
  # stage {
  #   name = "Source"

  #   action {
  #     name             = "Source"
  #     category         = "Source"
  #     owner            = "AWS"
  #     provider         = "S3"
  #     version          = "1"
  #     output_artifacts = ["source_output"]

  #     configuration = {
  #       S3Bucket    = aws_s3_bucket.codepipeline_source_bucket.bucket
  #       S3ObjectKey = "source.zip"
  #     }
  #   }
  # }

  # Github Source
  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = aws_codestarconnections_connection.connection.arn
        FullRepositoryId = var.repository_id
        BranchName       = var.repository_branch
      }
    }
  }

  stage {
    name = "Plan"

    action {
      name             = "Plan"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]
      version          = "1"

      configuration = {
        ProjectName = aws_codebuild_project.lambda_build_plan.name
      }
    }
  }

  stage {
    name = "Approve"

    action {
      name     = "Approve"
      category = "Approval"
      owner    = "AWS"
      provider = "Manual"
      version  = "1"
    }
  }

  stage {
    name = "Apply"

    action {
      name             = "Apply"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output", "build_output"]
      output_artifacts = []
      version          = "1"

      configuration = {
        ProjectName   = aws_codebuild_project.lambda_build_apply.name
        PrimarySource = "source_output"
      }
    }
  }
}

resource "aws_codepipeline" "lambda_destroy" {
  name     = var.destroy_pipeline_name
  role_arn = aws_iam_role.codepipeline_role.arn

  pipeline_type = "V2"

  artifact_store {
    location = aws_s3_bucket.codepipeline_artifact_bucket.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = aws_codestarconnections_connection.connection.arn
        FullRepositoryId = var.repository_id
        BranchName       = var.repository_branch
      }
    }
  }

  stage {
    name = "Plan"

    action {
      name             = "Plan"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]
      version          = "1"

      configuration = {
        ProjectName = aws_codebuild_project.lambda_build_plan_destroy.name
      }
    }
  }

  stage {
    name = "Approve"

    action {
      name     = "Approve"
      category = "Approval"
      owner    = "AWS"
      provider = "Manual"
      version  = "1"
    }
  }

  stage {
    name = "Apply"

    action {
      name             = "Apply"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output", "build_output"]
      output_artifacts = []
      version          = "1"

      configuration = {
        ProjectName   = aws_codebuild_project.lambda_build_apply_destroy.name
        PrimarySource = "source_output"
      }
    }
  }
}