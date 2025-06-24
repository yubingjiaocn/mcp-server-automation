"""Tests for configuration parsing and validation in config.py"""

import unittest
from unittest.mock import patch
import tempfile
import os

from mcp_server_automation.config import (
    ConfigLoader,
)


class TestConfigParsing(unittest.TestCase):
    """Test configuration parsing functions."""

    def test_parse_basic_build_config(self):
        """Test parsing basic build configuration."""
        config_data = {
            "build": {
                "github_url": "https://github.com/user/repo",
                "push_to_ecr": True,
                "aws_region": "us-west-2",
            }
        }

        with patch(
            "mcp_server_automation.config.ConfigLoader._get_aws_region",
            return_value="us-east-1",
        ):
            with patch(
                "mcp_server_automation.config.ConfigLoader._generate_default_ecr_repository",
                return_value="123.dkr.ecr.us-west-2.amazonaws.com/mcp-servers",
            ):
                result = ConfigLoader._parse_config(config_data)

        self.assertIsNotNone(result.build)
        self.assertEqual(result.build.github_url, "https://github.com/user/repo")
        self.assertEqual(result.build.aws_region, "us-west-2")
        self.assertTrue(result.build.push_to_ecr)
        self.assertEqual(result.build.image_name, "repo")

    def test_parse_build_config_with_overrides(self):
        """Test parsing build config with command override and environment variables."""
        config_data = {
            "build": {
                "github_url": "https://github.com/user/my-server",
                "command_override": ["python", "-m", "server", "--debug"],
                "environment_variables": {"LOG_LEVEL": "DEBUG", "API_KEY": "test-key"},
                "subfolder": "mcp-server",
                "branch": "develop",
            }
        }

        with patch(
            "mcp_server_automation.config.ConfigLoader._get_aws_region",
            return_value="us-east-1",
        ):
            result = ConfigLoader._parse_config(config_data)

        self.assertIsNotNone(result.build)
        self.assertEqual(
            result.build.command_override, ["python", "-m", "server", "--debug"]
        )
        self.assertEqual(
            result.build.environment_variables,
            {"LOG_LEVEL": "DEBUG", "API_KEY": "test-key"},
        )
        self.assertEqual(result.build.subfolder, "mcp-server")
        self.assertEqual(result.build.branch, "develop")
        self.assertEqual(result.build.image_name, "my-server-mcp-server")

    def test_parse_deploy_config(self):
        """Test parsing deploy configuration."""
        config_data = {
            "deploy": {
                "enabled": True,
                "service_name": "my-mcp-service",
                "cluster_name": "mcp-cluster",
                "vpc_id": "vpc-123456",
                "alb_subnet_ids": ["subnet-1", "subnet-2"],
                "ecs_subnet_ids": ["subnet-3"],
                "cpu": 512,
                "memory": 1024,
                "certificate_arn": "arn:aws:acm:us-west-2:123456789012:certificate/cert-id",
            }
        }

        with patch(
            "mcp_server_automation.config.ConfigLoader._get_aws_region",
            return_value="us-east-1",
        ):
            result = ConfigLoader._parse_config(config_data)

        self.assertIsNotNone(result.deploy)
        self.assertTrue(result.deploy.enabled)
        self.assertEqual(result.deploy.service_name, "my-mcp-service")
        self.assertEqual(result.deploy.cluster_name, "mcp-cluster")
        self.assertEqual(result.deploy.vpc_id, "vpc-123456")
        self.assertEqual(result.deploy.alb_subnet_ids, ["subnet-1", "subnet-2"])
        self.assertEqual(result.deploy.ecs_subnet_ids, ["subnet-3"])
        self.assertEqual(result.deploy.cpu, 512)
        self.assertEqual(result.deploy.memory, 1024)
        self.assertEqual(
            result.deploy.certificate_arn,
            "arn:aws:acm:us-west-2:123456789012:certificate/cert-id",
        )

    def test_parse_deploy_config_legacy_subnets(self):
        """Test parsing deploy config with legacy subnet_ids."""
        config_data = {
            "deploy": {
                "enabled": True,
                "service_name": "my-service",
                "cluster_name": "my-cluster",
                "vpc_id": "vpc-123",
                "subnet_ids": ["subnet-1", "subnet-2", "subnet-3"],
            }
        }

        with patch(
            "mcp_server_automation.config.ConfigLoader._get_aws_region",
            return_value="us-east-1",
        ):
            result = ConfigLoader._parse_config(config_data)

        self.assertIsNotNone(result.deploy)
        # Legacy subnet_ids should be used for both ALB and ECS
        self.assertEqual(
            result.deploy.alb_subnet_ids, ["subnet-1", "subnet-2", "subnet-3"]
        )
        self.assertEqual(
            result.deploy.ecs_subnet_ids, ["subnet-1", "subnet-2", "subnet-3"]
        )
        self.assertEqual(result.deploy.subnet_ids, ["subnet-1", "subnet-2", "subnet-3"])

    def test_parse_image_uri(self):
        """Test parsing image URI into components."""
        image_uri = (
            "123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-servers/my-server:latest"
        )

        image_name, ecr_repository = ConfigLoader._parse_image_uri(image_uri)

        self.assertEqual(image_name, "my-server")
        self.assertEqual(
            ecr_repository, "123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-servers"
        )

    def test_parse_image_uri_invalid(self):
        """Test parsing invalid image URI raises error."""
        with self.assertRaises(ValueError):
            ConfigLoader._parse_image_uri("invalid-uri")

    def test_generate_image_name_simple(self):
        """Test generating image name from GitHub URL."""
        result = ConfigLoader._generate_image_name(
            "https://github.com/user/my-awesome-server"
        )
        self.assertEqual(result, "my-awesome-server")

    def test_generate_image_name_with_subfolder(self):
        """Test generating image name with subfolder."""
        result = ConfigLoader._generate_image_name(
            "https://github.com/user/repo", "servers/mcp-server"
        )
        self.assertEqual(result, "repo-servers-mcp-server")

    def test_generate_image_name_with_git_extension(self):
        """Test generating image name from GitHub URL with .git extension."""
        result = ConfigLoader._generate_image_name(
            "https://github.com/user/my-server.git"
        )
        self.assertEqual(result, "my-server")

    def test_load_config_from_file(self):
        """Test loading configuration from YAML file."""
        config_content = """
build:
  github_url: https://github.com/test/repo
  push_to_ecr: false
  command_override:
    - python
    - server.py
  environment_variables:
    DEBUG: "true"

deploy:
  enabled: false
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with patch(
                "mcp_server_automation.config.ConfigLoader._get_aws_region",
                return_value="us-east-1",
            ):
                result = ConfigLoader.load_config(config_path)

            self.assertIsNotNone(result.build)
            self.assertEqual(result.build.github_url, "https://github.com/test/repo")
            self.assertEqual(result.build.command_override, ["python", "server.py"])
            self.assertEqual(result.build.environment_variables, {"DEBUG": "true"})
            self.assertFalse(result.build.push_to_ecr)
        finally:
            os.unlink(config_path)

    def test_load_config_file_not_found(self):
        """Test loading non-existent config file raises error."""
        with self.assertRaises(FileNotFoundError):
            ConfigLoader.load_config("/nonexistent/path/config.yaml")


class TestConfigValidation(unittest.TestCase):
    """Test configuration validation."""

    def test_subnet_ids_string_parsing(self):
        """Test that comma-separated subnet ID strings are parsed correctly."""
        config_data = {
            "deploy": {
                "enabled": True,
                "alb_subnet_ids": "subnet-1, subnet-2, subnet-3",
                "ecs_subnet_ids": "subnet-4,subnet-5",
            }
        }

        with patch(
            "mcp_server_automation.config.ConfigLoader._get_aws_region",
            return_value="us-east-1",
        ):
            result = ConfigLoader._parse_config(config_data)

        self.assertEqual(
            result.deploy.alb_subnet_ids, ["subnet-1", "subnet-2", "subnet-3"]
        )
        self.assertEqual(result.deploy.ecs_subnet_ids, ["subnet-4", "subnet-5"])


if __name__ == "__main__":
    unittest.main()
