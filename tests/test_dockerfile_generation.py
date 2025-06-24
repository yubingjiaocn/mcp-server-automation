"""Tests for Dockerfile generation (without actual Docker builds)"""

import unittest
from unittest.mock import patch
import tempfile
import os

from mcp_server_automation.build import BuildCommand


class TestDockerfileGeneration(unittest.TestCase):
    """Test Dockerfile generation without actual Docker builds."""

    def setUp(self):
        self.build_cmd = BuildCommand()

    def test_generate_dockerfile_with_custom_path(self):
        """Test Dockerfile generation using custom dockerfile path."""
        custom_dockerfile_content = "FROM python:3.12\nRUN echo 'custom dockerfile'"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".dockerfile", delete=False
        ) as f:
            f.write(custom_dockerfile_content)
            custom_path = f.name

        try:
            result = self.build_cmd._generate_dockerfile("/tmp/mcp", custom_path)
            self.assertEqual(result, custom_dockerfile_content)
        finally:
            os.unlink(custom_path)

    def test_generate_dockerfile_pip_requirements(self):
        """Test Dockerfile generation with pip and requirements.txt."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create requirements.txt
            requirements_path = os.path.join(temp_dir, "requirements.txt")
            with open(requirements_path, "w") as f:
                f.write("requests>=2.25.0\nclick>=8.0.0\n")

            with patch(
                "mcp_server_automation.build.BuildCommand._extract_start_command_from_readme",
                return_value=None,
            ):
                result = self.build_cmd._generate_dockerfile(temp_dir, None)

            # Verify Dockerfile contains pip installation
            self.assertIn(
                "pip install --no-cache-dir -r mcp-server/requirements.txt", result
            )
            self.assertIn("FROM python:3.12-alpine AS python-builder", result)
            self.assertIn("FROM node:24-bullseye AS runtime", result)
            self.assertIn("npm install -g mcp-proxy", result)

    def test_generate_dockerfile_uv_pyproject(self):
        """Test Dockerfile generation with uv and pyproject.toml."""
        pyproject_content = """
[tool.uv]
dev-dependencies = ["pytest>=6.0"]

[project]
name = "my-server"
dependencies = ["requests"]

[project.scripts]
my-server = "my_server:main"
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            pyproject_path = os.path.join(temp_dir, "pyproject.toml")
            with open(pyproject_path, "w") as f:
                f.write(pyproject_content)

            with patch(
                "mcp_server_automation.build.BuildCommand._extract_start_command_from_readme",
                return_value=None,
            ):
                result = self.build_cmd._generate_dockerfile(temp_dir, None)

            # Verify Dockerfile contains uv installation and usage
            self.assertIn("pip install --no-cache-dir uv", result)
            self.assertIn("uv sync --frozen --no-dev --no-editable", result)
            self.assertIn(
                'ENTRYPOINT ["mcp-proxy", "--debug", "--port", "8000", "--shell", "my-server"]',
                result,
            )

    def test_generate_dockerfile_poetry_pyproject(self):
        """Test Dockerfile generation with poetry and pyproject.toml."""
        pyproject_content = """
[tool.poetry]
name = "my-server"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.8"
requests = "^2.25.0"

[tool.poetry.scripts]
poetry-server = "my_server:main"
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            pyproject_path = os.path.join(temp_dir, "pyproject.toml")
            with open(pyproject_path, "w") as f:
                f.write(pyproject_content)

            with patch(
                "mcp_server_automation.build.BuildCommand._extract_start_command_from_readme",
                return_value=None,
            ):
                with patch(
                    "mcp_server_automation.build.BuildCommand._extract_start_command_from_pyproject",
                    return_value=["poetry-server"],
                ):
                    result = self.build_cmd._generate_dockerfile(temp_dir, None)

            # Verify Dockerfile contains poetry installation and usage
            self.assertIn("pip install --no-cache-dir poetry", result)
            self.assertIn("poetry config virtualenvs.create false", result)
            self.assertIn("poetry install --no-dev", result)
            self.assertIn(
                'ENTRYPOINT ["mcp-proxy", "--debug", "--port", "8000", "--shell", "poetry-server"]',
                result,
            )

    def test_generate_dockerfile_setup_py(self):
        """Test Dockerfile generation with setup.py."""
        setup_content = """
from setuptools import setup

setup(
    name="my-server",
    entry_points={
        'console_scripts': [
            'setup-server=my_server:main',
        ],
    },
)
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            setup_path = os.path.join(temp_dir, "setup.py")
            with open(setup_path, "w") as f:
                f.write(setup_content)

            with patch(
                "mcp_server_automation.build.BuildCommand._extract_start_command_from_readme",
                return_value=None,
            ):
                with patch(
                    "mcp_server_automation.build.BuildCommand._extract_start_command_from_setup_py",
                    return_value=["setup-server"],
                ):
                    result = self.build_cmd._generate_dockerfile(temp_dir, None)

            # Verify Dockerfile contains setup.py installation
            self.assertIn("pip install --no-cache-dir .", result)
            self.assertIn(
                'ENTRYPOINT ["mcp-proxy", "--debug", "--port", "8000", "--shell", "setup-server"]',
                result,
            )

    def test_generate_dockerfile_with_environment_variables(self):
        """Test Dockerfile generation with custom environment variables."""
        env_vars = {"LOG_LEVEL": "DEBUG", "API_KEY": "test-key-123", "PORT": "8080"}

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "mcp_server_automation.build.BuildCommand._extract_start_command_from_readme",
                return_value=None,
            ):
                result = self.build_cmd._generate_dockerfile(
                    temp_dir, None, None, env_vars
                )

            # Verify environment variables are set in Dockerfile
            self.assertIn('ENV LOG_LEVEL="DEBUG"', result)
            self.assertIn('ENV API_KEY="test-key-123"', result)
            self.assertIn('ENV PORT="8080"', result)

    def test_generate_dockerfile_with_command_override(self):
        """Test Dockerfile generation with command override."""
        command_override = ["python", "-m", "custom_server", "--debug"]

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.build_cmd._generate_dockerfile(
                temp_dir, None, command_override
            )

            # Verify the command override is used in the entrypoint
            expected_entrypoint = '["mcp-proxy", "--debug", "--port", "8000", "--shell", "python", "--", "-m", "custom_server", "--debug"]'
            self.assertIn(f"ENTRYPOINT {expected_entrypoint}", result)

    def test_generate_dockerfile_fallback_command(self):
        """Test Dockerfile generation with fallback command detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create server.py to trigger fallback detection
            server_path = os.path.join(temp_dir, "server.py")
            with open(server_path, "w") as f:
                f.write("# MCP server")

            with patch(
                "mcp_server_automation.build.BuildCommand._extract_start_command_from_readme",
                return_value=None,
            ):
                result = self.build_cmd._generate_dockerfile(temp_dir, None)

            # Verify fallback command is used
            self.assertIn(
                'ENTRYPOINT ["mcp-proxy", "--debug", "--port", "8000", "--shell", "python", "--", "server.py"]',
                result,
            )

    def test_generate_dockerfile_complete_structure(self):
        """Test that generated Dockerfile has all required sections."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "mcp_server_automation.build.BuildCommand._extract_start_command_from_readme",
                return_value=None,
            ):
                result = self.build_cmd._generate_dockerfile(temp_dir, None)

            # Verify all required sections are present
            self.assertIn("FROM python:3.12-alpine AS python-builder", result)
            self.assertIn("FROM node:24-bullseye AS runtime", result)
            self.assertIn("npm install -g mcp-proxy", result)
            self.assertIn("curl -LsSf https://astral.sh/uv/install.sh", result)
            self.assertIn("COPY --from=python-builder", result)
            self.assertIn('ENV PYTHONPATH="/app/mcp-server:$PYTHONPATH"', result)
            self.assertIn("HEALTHCHECK", result)
            self.assertIn("EXPOSE 8000", result)
            self.assertIn("ENTRYPOINT", result)

    def test_generate_dockerfile_no_environment_variables(self):
        """Test Dockerfile generation without environment variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "mcp_server_automation.build.BuildCommand._extract_start_command_from_readme",
                return_value=None,
            ):
                result = self.build_cmd._generate_dockerfile(temp_dir, None, None, None)

            # Should not contain custom ENV statements (other than PYTHONPATH and PATH)
            lines = result.split("\n")
            env_lines = [
                line
                for line in lines
                if line.strip().startswith("ENV ")
                and "PYTHONPATH" not in line
                and "PATH" not in line
            ]

            # Should only have the default environment variables
            self.assertEqual(len(env_lines), 0)


if __name__ == "__main__":
    unittest.main()
