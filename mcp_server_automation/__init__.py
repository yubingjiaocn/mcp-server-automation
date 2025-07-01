"""MCP Server Automation CLI Package."""

__version__ = "1.0.0"
__author__ = "MCP Server Automation"
__email__ = "mcp-automation@example.com"
__description__ = "CLI tool to automate MCP server deployment to AWS ECS"

from .cli import cli
from .__main__ import main

__all__ = ["cli", "main"]
