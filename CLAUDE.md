# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP Server Automation CLI tool that automates the process of transforming Model Context Protocol (MCP) stdio servers into Docker images deployed on AWS ECS using mcp-proxy. The tool bridges the gap between local MCP servers and remote HTTP-based deployments.

## Common Commands

### Development Setup
```bash
# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Install in development mode (optional - for local CLI usage)
pip install -e .
```

### Build and Deploy MCP Servers

#### Using uvx (Recommended)
```bash
# Build MCP server Docker image (local only)
uvx mcp-server-automation --config config-examples/local-build.yaml

# Build and push to ECR  
uvx mcp-server-automation --config config-examples/build-only.yaml

# Build, push to ECR, and deploy to ECS
uvx mcp-server-automation --config test-aws-docs.yaml

# Install and run from GitHub repository
uvx --from git+https://github.com/awslabs/mcp-server-automation mcp-server-automation --config my-config.yaml
```

#### Using Python directly
```bash
# Build MCP server Docker image (local only)
python -m mcp_server_automation --config test-aws-docs.yaml

# Build and push to ECR  
python -m mcp_server_automation --config config-with-ecr.yaml

# Build, push to ECR, and deploy to ECS
python -m mcp_server_automation --config test-aws-docs.yaml
```

#### Using local development setup
```bash
# Build MCP server Docker image (local only)
python -m mcp_server_automation --config test-aws-docs.yaml

# Or using the CLI directly
mcp-automate --config test-aws-docs.yaml
```

### Testing with MCP Inspector
```bash
# Test built Docker containers (using dynamic tags)
docker run -p 8000:8000 mcp-local/mcp-src-aws-documentation-mcp-server:a1b2c3d4-20231222-143055

# Use MCP inspector to test endpoints (updated to /mcp endpoint)
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

## Architecture

### Core Components

1. **BuildCommand** (`build.py`): Handles fetching MCP servers from GitHub, analyzing dependencies, generating Dockerfiles, and building/pushing images
2. **DeployCommand** (`deploy.py`): Manages ECS deployment using CloudFormation templates with ALB configuration  
3. **ConfigLoader** (`config.py`): Parses YAML configuration files with build and deploy specifications
4. **MCPConfigGenerator** (`mcp_config.py`): Generates client configuration for Claude Desktop, Cline, and other MCP clients

### Build Process Flow

1. **Repository Analysis**: Downloads GitHub repos and detects MCP server configuration from README files
2. **Command Detection**: Parses JSON blocks in README files to extract MCP server start commands, prioritizing NPX/uvx over Docker commands
3. **Dockerfile Generation**: Uses Jinja2 templates to create multi-stage Docker builds with mcp-proxy CLI integration
4. **Image Building**: Creates hybrid Node.js + Python containers with proper dependency management

### Key Technical Details

- **mcp-proxy Integration**: Uses TypeScript/Node.js CLI tool from https://github.com/punkpeye/mcp-proxy for HTTP transport
- **Container Architecture**: Multi-stage builds with `node:24-bullseye` base image, includes netcat for health checks
- **Command Format**: `mcp-proxy --port 8000 --shell <command> -- <args>` for proper argument ordering
- **Transport Protocol**: Converts MCP stdio to HTTP with `/mcp` endpoint for Streamable HTTP transport
- **Dynamic Tagging**: Images tagged with git commit hash and timestamp (e.g., `a1b2c3d4-20231222-143055`)
- **Branch Support**: Can build from specific git branches, defaults to 'main'

### Configuration System

Uses YAML files with separate `build` and `deploy` sections:
- `build`: GitHub URL, branch selection, image naming, ECR settings, dependency detection
- `deploy`: ECS cluster, VPC/subnet configuration, resource sizing, SSL certificates, MCP config generation

### Infrastructure Deployment

- **CloudFormation**: Complete infrastructure as code with VPC, ALB, ECS Fargate service
- **Security Groups**: Proper network isolation between ALB and ECS tasks
- **Health Checks**: Container uses netcat port checking, ALB health checks `/mcp` endpoint expecting HTTP 400
- **Session Stickiness**: ALB cookie-based stickiness for MCP client compatibility
- **Error Handling**: Graceful handling of CloudFormation "No updates" errors

## File Structure

- `build.py`: Core build logic with README parsing and Docker image creation
- `deploy.py`: ECS deployment with CloudFormation stack management
- `cli.py`: Click-based CLI interface with build/deploy commands
- `config.py`: YAML configuration parsing with auto-generation features
- `mcp_config.py`: Client configuration generation for deployed services
- `templates/Dockerfile.j2`: Jinja2 template for Docker image generation
- `templates/ecs-service.yaml`: CloudFormation template for AWS infrastructure

## Testing

The project includes test configurations primarily for AWS documentation MCP server:
- `test-aws-docs.yaml`: Configuration for AWS documentation MCP server (recommended)
- `test-filesystem-reference.yaml`: Reference configuration for filesystem MCP server (has Node.js argument handling issues)

Use `test-aws-docs.yaml` for validation when making changes to the build or deployment logic. The AWS Documentation MCP Server is more reliable than the filesystem server due to Python-based implementation vs Node.js argument parsing complexities.

## Configuration Options

### Build Section
- `github_url`: GitHub repository URL
- `subfolder`: Path to MCP server within repository (optional)
- `branch`: Git branch to build from (optional, defaults to 'main')
- `push_to_ecr`: Whether to push to ECR registry
- `image_name`: Custom image name (optional, auto-generated if not provided)
- `ecr_repository`: Custom ECR repository URL (optional)
- `aws_region`: AWS region for ECR (optional, defaults to profile region)

### Deploy Section
- `enabled`: Whether to deploy to ECS
- `service_name`: ECS service name
- `cluster_name`: ECS cluster name
- `vpc_id`: VPC ID for deployment
- `alb_subnet_ids`: Public subnet IDs for ALB (minimum 2)
- `ecs_subnet_ids`: Private subnet IDs for ECS tasks (minimum 1)
- `save_config`: File path to save MCP client configuration (optional)
- `certificate_arn`: SSL certificate ARN for HTTPS (optional)