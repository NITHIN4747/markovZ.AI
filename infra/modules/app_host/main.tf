# Security Group
resource "aws_security_group" "app_sg" {
  name        = "market-ai-${var.environment}-sg"
  description = "Allow inbound traffic for web and API"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Frontend (React)"
    from_port   = 5173
    to_port     = 5173
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Backend API (FastAPI)"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# IAM Role for EC2 to access SSM Parameters
resource "aws_iam_role" "ec2_role" {
  name = "market-ai-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "ssm_access" {
  name        = "market-ai-${var.environment}-ssm-policy"
  description = "Allow EC2 to read SSM parameters"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:*:*:parameter/market-ai/${var.environment}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.ssm_access.arn
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "market-ai-${var.environment}-profile"
  role = aws_iam_role.ec2_role.name
}

# Get latest Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

# EC2 Instance
resource "aws_instance" "app" {
  ami                  = data.aws_ami.ubuntu.id
  instance_type        = var.instance_type
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids = [aws_security_group.app_sg.id]

  # Ensure we stay strictly under the 30GB AWS Free Tier limit
  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  # User data to install docker, clone repo, and start
  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y apt-transport-https ca-certificates curl software-properties-common git jq awscli
              curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
              add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
              apt-get update
              apt-get install -y docker-ce docker-compose-plugin
              systemctl start docker
              systemctl enable docker
              usermod -aG docker ubuntu

              # Fetch secrets from SSM
              cd /home/ubuntu
              mkdir markovZ.AI
              cd markovZ.AI
              
              export GEMINI_API_KEY=$(aws ssm get-parameter --name /market-ai/${var.environment}/gemini-api-key --with-decryption --query Parameter.Value --output text --region ap-south-1)
              
              # Write .env file
              echo "GEMINI_API_KEY=$GEMINI_API_KEY" > .env
              
              # Note: In a real deploy, we would clone the repo here:
              # git clone https://github.com/NITHIN4747/markovZ.AI.git .
              # docker compose up -d
              EOF

  tags = {
    Name        = "market-ai-${var.environment}"
    Environment = var.environment
  }
}
