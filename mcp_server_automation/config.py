"""Configuration management for MCP automation."""

import yaml
import boto3
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class BuildConfig:
    """Configuration for build command."""

    github_url: str
    image_name: Optional[str] = None
    image_uri: Optional[str] = None
    ecr_repository: Optional[str] = None
    subfolder: Optional[str] = None
    branch: Optional[str] = None
    aws_region: str = "us-east-1"
    dockerfile_path: Optional[str] = None
    push_to_ecr: bool = False
    command_override: Optional[list[str]] = None
    environment_variables: Optional[Dict[str, str]] = None


@dataclass
class DeployConfig:
    """Configuration for deploy command."""

    enabled: bool = False
    service_name: Optional[str] = None
    cluster_name: Optional[str] = None
    vpc_id: Optional[str] = None
    alb_subnet_ids: Optional[list[str]] = None  # Public subnets for ALB
    ecs_subnet_ids: Optional[list[str]] = None  # Private subnets for ECS tasks
    subnet_ids: Optional[list[str]] = None  # Legacy field for backwards compatibility
    aws_region: str = "us-east-1"
    port: int = 8000
    cpu: int = 256
    memory: int = 512
    certificate_arn: Optional[str] = None
    save_config: Optional[str] = None


@dataclass
class MCPConfig:
    """Main configuration containing build and deploy configs."""

    build: Optional[BuildConfig] = None
    deploy: Optional[DeployConfig] = None


class ConfigLoader:
    """Loads and validates YAML configuration files."""

    @staticmethod
    def load_config(config_path: str) -> MCPConfig:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)

        return ConfigLoader._parse_config(config_data)

    @staticmethod
    def _parse_config(config_data: Dict[str, Any]) -> MCPConfig:
        """Parse configuration data into MCPConfig."""
        build_config = None
        deploy_config = None

        if "build" in config_data:
            build_data = config_data["build"]
            aws_region = build_data.get("aws_region", ConfigLoader._get_aws_region())
            push_to_ecr = build_data.get("push_to_ecr", False)

            # Handle image_uri vs image_name/ecr_repository
            image_uri = build_data.get("image_uri")
            image_name = None
            ecr_repository = None

            if image_uri:
                # Extract image_name and ecr_repository from image_uri
                image_name, ecr_repository = ConfigLoader._parse_image_uri(image_uri)
            else:
                # Generate image_name and ecr_repository as before
                image_name = build_data.get("image_name")
                if not image_name:
                    github_url = build_data["github_url"]
                    subfolder = build_data.get("subfolder")
                    image_name = ConfigLoader._generate_image_name(
                        github_url, subfolder
                    )

                ecr_repository = build_data.get("ecr_repository")
                if not ecr_repository and push_to_ecr:
                    ecr_repository = ConfigLoader._generate_default_ecr_repository(
                        aws_region
                    )

                # Generate image_uri from components
                if push_to_ecr and ecr_repository:
                    image_uri = f"{ecr_repository}/{image_name}:latest"

            build_config = BuildConfig(
                github_url=build_data["github_url"],
                image_name=image_name,
                image_uri=image_uri,
                ecr_repository=ecr_repository,
                subfolder=build_data.get("subfolder"),
                branch=build_data.get("branch"),
                aws_region=aws_region,
                dockerfile_path=build_data.get("dockerfile_path"),
                push_to_ecr=push_to_ecr,
                command_override=build_data.get("command_override"),
                environment_variables=build_data.get("environment_variables"),
            )

        if "deploy" in config_data:
            deploy_data = config_data["deploy"]
            enabled = deploy_data.get("enabled", False)

            # Handle new subnet structure
            alb_subnet_ids = None
            ecs_subnet_ids = None
            subnet_ids = None  # Legacy

            if "alb_subnet_ids" in deploy_data:
                alb_subnet_ids = deploy_data["alb_subnet_ids"]
                if isinstance(alb_subnet_ids, str):
                    alb_subnet_ids = [s.strip() for s in alb_subnet_ids.split(",")]

            if "ecs_subnet_ids" in deploy_data:
                ecs_subnet_ids = deploy_data["ecs_subnet_ids"]
                if isinstance(ecs_subnet_ids, str):
                    ecs_subnet_ids = [s.strip() for s in ecs_subnet_ids.split(",")]

            # Legacy support: if subnet_ids provided but not alb/ecs specific ones
            if "subnet_ids" in deploy_data:
                subnet_ids = deploy_data["subnet_ids"]
                if isinstance(subnet_ids, str):
                    subnet_ids = [s.strip() for s in subnet_ids.split(",")]

                # Use legacy subnet_ids for both ALB and ECS if new fields not specified
                if not alb_subnet_ids:
                    alb_subnet_ids = subnet_ids
                if not ecs_subnet_ids:
                    ecs_subnet_ids = subnet_ids

            deploy_config = DeployConfig(
                enabled=enabled,
                service_name=deploy_data.get("service_name"),
                cluster_name=deploy_data.get("cluster_name"),
                vpc_id=deploy_data.get("vpc_id"),
                alb_subnet_ids=alb_subnet_ids,
                ecs_subnet_ids=ecs_subnet_ids,
                subnet_ids=subnet_ids,
                aws_region=deploy_data.get(
                    "aws_region", ConfigLoader._get_aws_region()
                ),
                port=deploy_data.get("port", 8000),
                cpu=deploy_data.get("cpu", 256),
                memory=deploy_data.get("memory", 512),
                certificate_arn=deploy_data.get("certificate_arn"),
                save_config=deploy_data.get("save_config"),
            )

        return MCPConfig(build=build_config, deploy=deploy_config)

    @staticmethod
    def _generate_image_name(github_url: str, subfolder: Optional[str] = None) -> str:
        """Generate simple image name from GitHub URL."""
        repo_name = github_url.rstrip(".git").split("/")[-1]
        if subfolder:
            subfolder_name = subfolder.strip("/").replace("/", "-")
            return f"{repo_name}-{subfolder_name}"
        return repo_name

    @staticmethod
    def _get_aws_region() -> str:
        """Get AWS region from profile or default to us-east-1."""
        try:
            session = boto3.Session()
            return session.region_name or "us-east-1"
        except Exception:
            return "us-east-1"

    @staticmethod
    def _parse_image_uri(image_uri: str) -> tuple[str, str]:
        """Parse image URI to extract image name and ECR repository base.

        Args:
            image_uri: Full image URI like '123.dkr.ecr.us-east-1.amazonaws.com/repo/image:tag'

        Returns:
            tuple: (image_name, ecr_repository_base)
        """
        try:
            # Split by '/' to get parts
            parts = image_uri.split("/")
            if len(parts) < 2:
                raise ValueError("Invalid image URI format")

            # Last part contains image:tag
            image_with_tag = parts[-1]
            image_name = image_with_tag.split(":")[0]  # Remove tag

            # Everything before the last '/' is the registry/repository base
            ecr_repository = "/".join(parts[:-1])

            return image_name, ecr_repository

        except Exception as e:
            raise ValueError(f"Failed to parse image URI '{image_uri}': {e}")

    @staticmethod
    def _generate_default_ecr_repository(aws_region: str) -> str:
        """Generate default ECR repository URI using AWS account ID."""
        sts_client = boto3.client("sts", region_name=aws_region)
        account_id = sts_client.get_caller_identity()["Account"]
        return f"{account_id}.dkr.ecr.{aws_region}.amazonaws.com/mcp-servers"
