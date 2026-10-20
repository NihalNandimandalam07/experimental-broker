resource "aws_ssm_document" "BlackHoleByIPAddress" {
  name            = "BlackHoleByIPAddress"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/BlackHoleByIPAddress.yml")

}

resource "aws_ssm_document" "BlackHoleByPort" {
  name            = "BlackHoleByPort"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/BlackHoleByPort.yml")

}

resource "aws_ssm_document" "BlackholeKafka" {
  name            = "BlackholeKafka"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/BlackHoleKafka.yml")

}

resource "aws_ssm_document" "BlockNetworkTrafficOnInstance" {
  name            = "BlockNetworkTrafficOnInstance"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/BlockNetworkTrafficOnInstance.yml")

}

resource "aws_ssm_document" "DeletePod" {
  name            = "DeletePod"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/DeletePod.yml")

}

resource "aws_ssm_document" "DetachVolume" {
  name            = "DetachVolume"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/DetachVolume.yml")

}

resource "aws_ssm_document" "DiskVolumeExhaustion" {
  name            = "DiskVolumeExhaustion"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/DiskVolumeExhaustion.yml")

}

resource "aws_ssm_document" "InstallStressNG" {
  name            = "InstallStressNG"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/InstallStressNG.yml")

}

resource "aws_ssm_document" "KillProcess" {
  name            = "KillProcess"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/KillProcess.yml")

}

resource "aws_ssm_document" "KillProcessByName" {
  name            = "KillProcessByName"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/KillProcessByName.yml")

}

resource "aws_ssm_document" "PodBlackholeByPort" {
  name            = "PodBlackholeByPort"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/PodBlackholeByPort.yml")

}

resource "aws_ssm_document" "PodHealthCheck" {
  name            = "PodHealthCheck"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/PodHealthCheck.yml")

}

resource "aws_ssm_document" "PodStressAllNetworkIO" {
  name            = "PodStressAllNetworkIO"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/PodStressAllNetworkIO.yml")

}

resource "aws_ssm_document" "PodStressCPU" {
  name            = "PodStressCPU"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/PodStressCPU.yml")

}

resource "aws_ssm_document" "PodStressIO" {
  name            = "PodStressIO"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/PodStressIO.yml")

}

resource "aws_ssm_document" "PodStressMemory" {
  name            = "PodStressMemory"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/PodStressMemory.yml")

}

resource "aws_ssm_document" "PodStressNetworkUtilization" {
  name            = "PodStressNetworkUtilization"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/PodStressNetworkUtilization.yml")

}

resource "aws_ssm_document" "PodTerminationCrash" {
  name            = "PodTerminationCrash"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/PodTerminationCrash.yml")

}

resource "aws_ssm_document" "ShutDownNetworkInterfaceOnInstance" {
  name            = "ShutDownNetworkInterfaceOnInstance"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/ShutDownNetworkInterfaceOnInstance.yml")

}

resource "aws_ssm_document" "StressAllNetworkIO" {
  name            = "StressAllNetworkIO"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/StressAllNetworkIO.yml")

}
resource "aws_ssm_document" "StressCPU" {
  name            = "StressCPU"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/StressCPU.yml")

}

resource "aws_ssm_document" "StressIO" {
  name            = "StressIO"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/StressIO.yml")

}

resource "aws_ssm_document" "StressNetworkLatency" {
  name            = "StressNetworkLatency"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/StressNetworkLatency.yml")

}

resource "aws_ssm_document" "StressMemory" {
  name            = "StressMemory"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/StressMemory.yml")

}

resource "aws_ssm_document" "StressPacketLoss" {
  name            = "StressPacketLoss"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/StressPacketLoss.yml")

}

resource "aws_ssm_document" "StressNetworkUtilization" {
  name            = "StressNetworkUtilization"
  document_type   = "Command"
  document_format = "YAML"

  content = file("${path.module}/documents/StressNetworkUtilization.yml")

}  