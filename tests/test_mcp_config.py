"""Tests for MCP configuration generation in mcp_config.py"""

import unittest
import tempfile
import os
import json

from mcp_server_automation.mcp_config import MCPConfigGenerator


class TestMCPConfigGeneration(unittest.TestCase):
    """Test MCP configuration generation functions."""

    def test_generate_sse_example_configs(self):
        """Test generating SSE configuration."""
        service_name = "my-mcp-server"
        alb_url = "https://my-alb.amazonaws.com"

        result = MCPConfigGenerator.generate_sse_example_configs(service_name, alb_url)

        config = json.loads(result)
        self.assertIn("mcpServers", config)
        self.assertIn(service_name, config["mcpServers"])
        self.assertEqual(config["mcpServers"][service_name]["type"], "sse")
        self.assertEqual(
            config["mcpServers"][service_name]["url"],
            ["https://my-alb.amazonaws.com/sse"],
        )

    def test_generate_sse_example_configs_with_description(self):
        """Test generating SSE configuration with description."""
        service_name = "aws-docs-server"
        alb_url = "https://docs-alb.com/"
        description = "AWS Documentation MCP Server"

        result = MCPConfigGenerator.generate_sse_example_configs(
            service_name, alb_url, description
        )

        config = json.loads(result)
        self.assertEqual(config["mcpServers"][service_name]["description"], description)
        self.assertEqual(
            config["mcpServers"][service_name]["url"], ["https://docs-alb.com/sse"]
        )

    def test_generate_streamable_http_example_configs(self):
        """Test generating Streamable HTTP configuration."""
        service_name = "my-http-server"
        alb_url = "https://http-server.example.com"

        result = MCPConfigGenerator.generate_streamable_http_example_configs(
            service_name, alb_url
        )

        config = json.loads(result)
        self.assertIn("mcpServers", config)
        self.assertIn(service_name, config["mcpServers"])
        self.assertEqual(config["mcpServers"][service_name]["transportType"], "http")
        self.assertEqual(
            config["mcpServers"][service_name]["url"],
            ["https://http-server.example.com/mcp"],
        )

    def test_generate_streamable_http_example_configs_with_description(self):
        """Test generating Streamable HTTP configuration with description."""
        service_name = "file-server"
        alb_url = "https://file-server.com/"
        description = "File System MCP Server"

        result = MCPConfigGenerator.generate_streamable_http_example_configs(
            service_name, alb_url, description
        )

        config = json.loads(result)
        self.assertEqual(config["mcpServers"][service_name]["description"], description)
        self.assertEqual(config["mcpServers"][service_name]["transportType"], "http")
        self.assertEqual(
            config["mcpServers"][service_name]["url"], ["https://file-server.com/mcp"]
        )

    def test_generate_configs_trailing_slash_handling(self):
        """Test that trailing slashes in URLs are handled correctly."""
        service_name = "test-server"
        alb_url_with_slash = "https://example.com/"
        alb_url_without_slash = "https://example.com"

        result_with_slash = MCPConfigGenerator.generate_sse_example_configs(
            service_name, alb_url_with_slash
        )
        result_without_slash = MCPConfigGenerator.generate_sse_example_configs(
            service_name, alb_url_without_slash
        )

        config_with_slash = json.loads(result_with_slash)
        config_without_slash = json.loads(result_without_slash)

        # Both should result in the same URL
        self.assertEqual(
            config_with_slash["mcpServers"][service_name]["url"],
            config_without_slash["mcpServers"][service_name]["url"],
        )
        self.assertEqual(
            config_with_slash["mcpServers"][service_name]["url"],
            ["https://example.com/sse"],
        )

    def test_print_setup_instructions(self):
        """Test generating complete setup instructions."""
        service_name = "test-service"
        alb_url = "https://test-alb.com"
        description = "Test MCP Server"

        result = MCPConfigGenerator.print_setup_instructions(
            service_name, alb_url, description
        )

        # Verify that the instructions contain expected sections
        self.assertIn("MCP Server Setup Instructions", result)
        self.assertIn(
            f"Your MCP server '{service_name}' has been deployed successfully!", result
        )
        self.assertIn(f"ALB URL: {alb_url}", result)
        self.assertIn("Configuration", result)
        self.assertIn("MCP Clients supports HTTP SSE", result)
        self.assertIn("MCP Clients supports Streamable HTTP", result)
        self.assertIn("Testing the Connection", result)
        self.assertIn("Troubleshooting", result)

        # Verify that both configuration types are included
        self.assertIn('"type": "sse"', result)
        self.assertIn('"transportType": "http"', result)
        self.assertIn("/sse", result)
        self.assertIn("/mcp", result)

        # Verify MCP inspector command is included
        self.assertIn(
            f"npx @modelcontextprotocol/inspector --cli {alb_url}/mcp", result
        )

        # Verify troubleshooting commands
        self.assertIn(f"curl -v {alb_url}/mcp", result)

    def test_save_config_creates_directory(self):
        """Test that save_config creates directories if they don't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "subdir", "config.json")
            test_config = {"test": "data"}

            MCPConfigGenerator.save_config(test_config, config_path)

            # Verify file was created
            self.assertTrue(os.path.exists(config_path))

            # Verify content is correct
            with open(config_path, "r") as f:
                saved_config = json.load(f)

            self.assertEqual(saved_config, test_config)

    def test_save_config_overwrites_existing(self):
        """Test that save_config overwrites existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")

            # Write initial config
            initial_config = {"initial": "data"}
            MCPConfigGenerator.save_config(initial_config, config_path)

            # Overwrite with new config
            new_config = {"new": "data", "more": "fields"}
            MCPConfigGenerator.save_config(new_config, config_path)

            # Verify new content
            with open(config_path, "r") as f:
                saved_config = json.load(f)

            self.assertEqual(saved_config, new_config)
            self.assertNotEqual(saved_config, initial_config)

    def test_json_formatting(self):
        """Test that generated JSON is properly formatted."""
        service_name = "format-test"
        alb_url = "https://format.test"

        sse_result = MCPConfigGenerator.generate_sse_example_configs(
            service_name, alb_url
        )
        http_result = MCPConfigGenerator.generate_streamable_http_example_configs(
            service_name, alb_url
        )

        # Verify JSON is properly formatted (indented)
        self.assertIn('  "mcpServers"', sse_result)
        self.assertIn('    "' + service_name + '"', sse_result)

        self.assertIn('  "mcpServers"', http_result)
        self.assertIn('    "' + service_name + '"', http_result)

        # Verify valid JSON
        json.loads(sse_result)  # Should not raise exception
        json.loads(http_result)  # Should not raise exception


class TestMCPConfigEdgeCases(unittest.TestCase):
    """Test edge cases for MCP configuration generation."""

    def test_empty_service_name(self):
        """Test behavior with empty service name."""
        result = MCPConfigGenerator.generate_sse_example_configs("", "https://test.com")
        config = json.loads(result)
        self.assertIn("", config["mcpServers"])

    def test_special_characters_in_service_name(self):
        """Test service names with special characters."""
        service_name = "my-server_v2.0"
        result = MCPConfigGenerator.generate_sse_example_configs(
            service_name, "https://test.com"
        )
        config = json.loads(result)
        self.assertIn(service_name, config["mcpServers"])

    def test_url_with_path(self):
        """Test URLs that already have paths."""
        service_name = "path-test"
        alb_url = "https://example.com/api/v1"

        result = MCPConfigGenerator.generate_sse_example_configs(service_name, alb_url)
        config = json.loads(result)

        # Should append /sse to the existing path
        self.assertEqual(
            config["mcpServers"][service_name]["url"],
            ["https://example.com/api/v1/sse"],
        )

    def test_url_with_query_params(self):
        """Test URLs with query parameters."""
        service_name = "query-test"
        alb_url = "https://example.com?param=value"

        result = MCPConfigGenerator.generate_streamable_http_example_configs(
            service_name, alb_url
        )
        config = json.loads(result)

        # Should append /mcp while preserving query params
        self.assertEqual(
            config["mcpServers"][service_name]["url"],
            ["https://example.com?param=value/mcp"],
        )


if __name__ == "__main__":
    unittest.main()
