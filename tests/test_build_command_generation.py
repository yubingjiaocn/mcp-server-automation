"""Tests for command generation and parsing functions in build.py"""

import unittest
from unittest.mock import patch
import tempfile
import os

from mcp_server_automation.build import BuildCommand


class TestCommandGeneration(unittest.TestCase):
    """Test command generation functions."""

    def setUp(self):
        self.build_cmd = BuildCommand()

    def test_generate_entrypoint_command_no_command(self):
        """Test entrypoint generation with no start command."""
        result = self.build_cmd._generate_entrypoint_command(None)
        expected = [
            "mcp-proxy",
            "--debug",
            "--port",
            "8000",
            "--shell",
            "python",
            "-m",
            "server",
        ]
        self.assertEqual(result, expected)

    def test_generate_entrypoint_command_single_command(self):
        """Test entrypoint generation with single command."""
        start_command = ["python-server"]
        result = self.build_cmd._generate_entrypoint_command(start_command)
        expected = [
            "mcp-proxy",
            "--debug",
            "--port",
            "8000",
            "--shell",
            "python-server",
        ]
        self.assertEqual(result, expected)

    def test_generate_entrypoint_command_with_args(self):
        """Test entrypoint generation with command and arguments."""
        start_command = ["python", "-m", "my_server", "--debug"]
        result = self.build_cmd._generate_entrypoint_command(start_command)
        expected = [
            "mcp-proxy",
            "--debug",
            "--port",
            "8000",
            "--shell",
            "python",
            "--",
            "-m",
            "my_server",
            "--debug",
        ]
        self.assertEqual(result, expected)

    def test_generate_entrypoint_command_with_multiple_args(self):
        """Test entrypoint generation with multiple arguments."""
        start_command = ["uvx", "mcp-server", "--port", "3000", "--verbose"]
        result = self.build_cmd._generate_entrypoint_command(start_command)
        expected = [
            "mcp-proxy",
            "--debug",
            "--port",
            "8000",
            "--shell",
            "uvx",
            "--",
            "mcp-server",
            "--port",
            "3000",
            "--verbose",
        ]
        self.assertEqual(result, expected)

    def test_generate_image_tag_with_branch(self):
        """Test image tag generation with branch."""
        with patch("requests.get") as mock_get:
            mock_response = mock_get.return_value
            mock_response.status_code = 200
            mock_response.json.return_value = {"sha": "abcd1234567890"}

            with patch("mcp_server_automation.build.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20231222-143055"

                result = self.build_cmd._generate_image_tag(
                    "https://github.com/user/repo", "feature-branch"
                )
                expected = "abcd1234-feature-branch-20231222-143055"
                self.assertEqual(result, expected)

    def test_generate_image_tag_without_branch(self):
        """Test image tag generation without branch."""
        with patch("requests.get") as mock_get:
            mock_response = mock_get.return_value
            mock_response.status_code = 200
            mock_response.json.return_value = {"sha": "abcd1234567890"}

            with patch("mcp_server_automation.build.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20231222-143055"

                result = self.build_cmd._generate_image_tag(
                    "https://github.com/user/repo"
                )
                expected = "abcd1234-20231222-143055"
                self.assertEqual(result, expected)

    def test_generate_image_tag_api_failure(self):
        """Test image tag generation when GitHub API fails."""
        with patch("requests.get") as mock_get:
            mock_response = mock_get.return_value
            mock_response.status_code = 404

            with patch("mcp_server_automation.build.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20231222-143055"

                result = self.build_cmd._generate_image_tag(
                    "https://github.com/user/repo"
                )
                expected = "nocommit-20231222-143055"
                self.assertEqual(result, expected)


class TestReadmeCommandExtraction(unittest.TestCase):
    """Test README command extraction functions."""

    def setUp(self):
        self.build_cmd = BuildCommand()

    def test_extract_start_command_from_readme_with_valid_json(self):
        """Test extracting command from README with valid MCP JSON."""
        readme_content = """
# My MCP Server

Configuration:
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["-m", "my_server", "--debug"]
    }
  }
}
```
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write(readme_content)

            result = self.build_cmd._extract_start_command_from_readme(temp_dir)
            expected = ["python", "-m", "my_server", "--debug"]
            self.assertEqual(result, expected)

    def test_extract_start_command_from_readme_skip_docker(self):
        """Test that Docker commands are skipped in favor of others."""
        readme_content = """
# My MCP Server

```json
{
  "mcpServers": {
    "docker-server": {
      "command": "docker",
      "args": ["run", "my-image"]
    },
    "python-server": {
      "command": "uvx",
      "args": ["my-server"]
    }
  }
}
```
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write(readme_content)

            result = self.build_cmd._extract_start_command_from_readme(temp_dir)
            expected = ["uvx", "my-server"]
            self.assertEqual(result, expected)

    def test_extract_start_command_from_readme_no_json(self):
        """Test README without valid JSON returns None."""
        readme_content = """
# My MCP Server

This is just text without JSON configuration.
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write(readme_content)

            result = self.build_cmd._extract_start_command_from_readme(temp_dir)
            self.assertIsNone(result)

    def test_extract_start_command_from_readme_no_file(self):
        """Test with no README file returns None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.build_cmd._extract_start_command_from_readme(temp_dir)
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
