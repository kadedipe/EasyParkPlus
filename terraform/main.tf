# parking-management/terraform/main.tf
provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  
  tags = {
    Name = "parking-vpc"
    Environment = var.environment
  }
}

# Subnets
resource "aws_subnet" "public" {
  count = 2
  vpc_id = aws_vpc.main.id
  cidr_block = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "parking-public-subnet-${count.index}"
    Environment = var.environment
  }
}

# Security Group
resource "aws_security_group" "frontend" {
  name = "parking-frontend-sg"
  description = "Security group for frontend"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port = 80
    to_port = 80
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "parking-frontend-sg"
    Environment = var.environment
  }
}

# ECR Repository
resource "aws_ecr_repository" "frontend" {
  name = "parking-frontend"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "parking-cluster"
}

# IAM Role for ECS
resource "aws_iam_role" "ecs_task_execution" {
  name = "parking-ecs-task-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Definition
resource "aws_ecs_task_definition" "frontend" {
  family = "parking-frontend"
  network_mode = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu = "256"
  memory = "512"
  execution_role_arn = aws_iam_role.ecs_task_execution.arn
  task_role_arn = aws_iam_role.ecs_task_execution.arn

  container_definitions = jsonencode([
    {
      name = "frontend"
      image = "${aws_ecr_repository.frontend.repository_url}:latest"
      portMappings = [
        {
          containerPort = 80
          protocol = "tcp"
        }
      ]
      environment = [
        { name = "NODE_ENV", value = "production" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group" = "/ecs/parking-frontend"
          "awslogs-region" = var.aws_region
          "awslogs-stream-prefix" = "frontend"
        }
      }
    }
  ])
}

# ECS Service
resource "aws_ecs_service" "frontend" {
  name = "parking-frontend-service"
  cluster = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count = 2
  launch_type = "FARGATE"
  
  network_configuration {
    subnets = aws_subnet.public[*].id
    security_groups = [aws_security_group.frontend.id]
    assign_public_ip = true
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name = "frontend"
    container_port = 80
  }
}

# Load Balancer
resource "aws_lb" "frontend" {
  name = "parking-frontend-lb"
  internal = false
  load_balancer_type = "application"
  security_groups = [aws_security_group.frontend.id]
  subnets = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "frontend" {
  name = "parking-frontend-tg"
  port = 80
  protocol = "HTTP"
  vpc_id = aws_vpc.main.id
  target_type = "ip"
  
  health_check {
    path = "/health"
    interval = 30
    timeout = 5
    healthy_threshold = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "frontend" {
  load_balancer_arn = aws_lb.frontend.arn
  port = 80
  protocol = "HTTP"
  
  default_action {
    type = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# Route53 Record
resource "aws_route53_record" "frontend" {
  zone_id = var.zone_id
  name = var.domain_name
  type = "A"
  alias {
    name = aws_lb.frontend.dns_name
    zone_id = aws_lb.frontend.zone_id
    evaluate_target_health = true
  }
}