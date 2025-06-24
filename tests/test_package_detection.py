"""Tests for package info detection functions in build.py"""

import unittest
from unittest.mock import patch
import tempfile
import os

from mcp_server_automation.build import BuildCommand


class TestPackageInfoDetection(unittest.TestCase):
    """Test package manager and dependency detection functions."""

    def setUp(self):
        self.build_cmd = BuildCommand()

    def test_detect_package_info_with_command_override(self):
        """Test package info detection with command override."""
        with tempfile.TemporaryDirectory() as temp_dir:
            command_override = ["python", "-m", "custom_server", "--port", "8080"]
            env_vars = {"DEBUG": "true", "PORT": "8080"}

            result = self.build_cmd._detect_package_info(
                temp_dir, command_override, env_vars
            )

            self.assertEqual(result["start_command"], command_override)
            self.assertEqual(result["environment_variables"], env_vars)
            self.assertEqual(result["manager"], "pip")
            expected_entrypoint = [
                "mcp-proxy",
                "--debug",
                "--port",
                "8000",
                "--shell",
                "python",
                "--",
                "-m",
                "custom_server",
                "--port",
                "8080",
            ]
            self.assertEqual(result["entrypoint_command"], expected_entrypoint)

    def test_detect_package_info_pyproject_toml_uv(self):
        """Test detection of uv package manager from pyproject.toml."""
        pyproject_content = """
[tool.uv]
dev-dependencies = ["pytest>=6.0"]

[project]
name = "my-mcp-server"
version = "0.1.0"
dependencies = ["requests"]

[project.scripts]
my-server = "my_server:main"
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            pyproject_path = os.path.join(temp_dir, "pyproject.toml")
            with open(pyproject_path, "w") as f:
                f.write(pyproject_content)

            result = self.build_cmd._detect_package_info(temp_dir)

            self.assertEqual(result["manager"], "uv")
            self.assertEqual(result["project_file"], "pyproject.toml")
            self.assertEqual(result["start_command"], ["my-server"])

    def test_detect_package_info_pyproject_toml_poetry(self):
        """Test detection of poetry package manager from pyproject.toml."""
        pyproject_content = """
[tool.poetry]
name = "my-server"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.8"
requests = "^2.25.0"

[project.scripts]
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
                result = self.build_cmd._detect_package_info(temp_dir)

            self.assertEqual(result["manager"], "poetry")
            self.assertEqual(result["project_file"], "pyproject.toml")
            self.assertEqual(result["start_command"], ["poetry-server"])

    def test_detect_package_info_requirements_txt(self):
        """Test detection of requirements.txt."""
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_path = os.path.join(temp_dir, "requirements.txt")
            with open(requirements_path, "w") as f:
                f.write("requests>=2.25.0\nclick>=8.0.0\n")

            result = self.build_cmd._detect_package_info(temp_dir)

            self.assertEqual(result["manager"], "pip")
            self.assertEqual(result["requirements_file"], "requirements.txt")

    def test_detect_package_info_setup_py(self):
        """Test detection of setup.py."""
        setup_content = """
from setuptools import setup

setup(
    name="my-server",
    version="0.1.0",
    entry_points={
        'console_scripts': [
            'setup-server=my_server.main:main',
            'other-script=my_server.other:run',
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
                    result = self.build_cmd._detect_package_info(temp_dir)

            self.assertEqual(result["manager"], "pip")
            self.assertEqual(result["project_file"], "setup.py")
            self.assertEqual(result["start_command"], ["setup-server"])

    def test_detect_fallback_start_command_server_py(self):
        """Test fallback detection finds server.py."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server_path = os.path.join(temp_dir, "server.py")
            with open(server_path, "w") as f:
                f.write('# MCP server\nprint("Hello")')

            result = self.build_cmd._detect_fallback_start_command(temp_dir)

            self.assertEqual(result, ["python", "server.py"])

    def test_detect_fallback_start_command_main_py(self):
        """Test fallback detection finds main.py."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_path = os.path.join(temp_dir, "main.py")
            with open(main_path, "w") as f:
                f.write("# Main entry point")

            result = self.build_cmd._detect_fallback_start_command(temp_dir)

            self.assertEqual(result, ["python", "main.py"])

    def test_detect_fallback_start_command_main_module(self):
        """Test fallback detection finds __main__.py."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.makedirs(os.path.join(temp_dir, "my_package"))
            main_path = os.path.join(temp_dir, "__main__.py")
            with open(main_path, "w") as f:
                f.write("# Main module")

            result = self.build_cmd._detect_fallback_start_command(temp_dir)

            expected = ["python", "-m", os.path.basename(temp_dir)]
            self.assertEqual(result, expected)

    def test_detect_fallback_start_command_mcp_pattern(self):
        """Test fallback detection finds files with 'mcp' in name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mcp_path = os.path.join(temp_dir, "mcp_server.py")
            with open(mcp_path, "w") as f:
                f.write("# MCP server implementation")

            result = self.build_cmd._detect_fallback_start_command(temp_dir)

            self.assertEqual(result, ["python", "mcp_server.py"])

    def test_detect_fallback_start_command_no_files(self):
        """Test fallback detection when no recognized files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some unrelated files
            with open(os.path.join(temp_dir, "config.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(temp_dir, "readme.txt"), "w") as f:
                f.write("Documentation")

            result = self.build_cmd._detect_fallback_start_command(temp_dir)

            # Should default to server.py
            self.assertEqual(result, ["python", "server.py"])

    def test_extract_start_command_from_pyproject_no_scripts(self):
        """Test pyproject.toml parsing when no console scripts exist."""
        pyproject_content = """
[project]
name = "my-server"
version = "0.1.0"
dependencies = ["requests"]
"""

        result = self.build_cmd._extract_start_command_from_pyproject(pyproject_content)
        self.assertIsNone(result)

    def test_extract_start_command_from_pyproject_entry_points(self):
        """Test pyproject.toml parsing with entry-points format."""
        pyproject_content = """
[project]
name = "my-server"
version = "0.1.0"

[project.entry-points.console_scripts]
entry-server = "my_server:main"
"""

        result = self.build_cmd._extract_start_command_from_pyproject(pyproject_content)
        self.assertEqual(result, ["entry-server"])

    def test_extract_start_command_from_setup_py_no_scripts(self):
        """Test setup.py parsing when no console scripts exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_content = """
from setuptools import setup

setup(
    name="my-server",
    version="0.1.0",
    packages=["my_server"],
)
"""
            setup_path = os.path.join(temp_dir, "setup.py")
            with open(setup_path, "w") as f:
                f.write(setup_content)

            result = self.build_cmd._extract_start_command_from_setup_py(temp_dir)
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
