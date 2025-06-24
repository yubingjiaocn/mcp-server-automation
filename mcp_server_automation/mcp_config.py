"""MCP configuration generator for deployed remote servers."""

import json
import os
from typing import Dict, Any


class MCPConfigGenerator:
    """Generates MCP client configurations for deployed remote servers."""

    @staticmethod
    def save_config(config: Dict[str, Any], file_path: str) -> None:
        """Save MCP configuration to file."""

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write configuration
        with open(file_path, "w") as f:
            json.dump(config, f, indent=2)

    @staticmethod
    def generate_sse_example_configs(
        service_name: str, alb_url: str, description: str = ""
    ) -> str:
        base_url = alb_url.rstrip("/")

        config = {
            "mcpServers": {service_name: {"type": "sse", "url": [f"{base_url}/sse"]}}
        }

        if description:
            config["mcpServers"][service_name]["description"] = description

        return json.dumps(config, indent=2)

    @staticmethod
    def generate_streamable_http_example_configs(
        service_name: str, alb_url: str, description: str = ""
    ) -> str:
        base_url = alb_url.rstrip("/")

        config = {
            "mcpServers": {
                service_name: {"transportType": "http", "url": [f"{base_url}/mcp"]}
            }
        }

        if description:
            config["mcpServers"][service_name]["description"] = description

        return json.dumps(config, indent=2)

    @staticmethod
    def print_setup_instructions(
        service_name: str, alb_url: str, description: str = ""
    ) -> str:
        """Generate setup instructions for the deployed MCP server."""

        configs_sse = MCPConfigGenerator.generate_sse_example_configs(
            service_name, alb_url, description
        )
        configs_streamable_http = (
            MCPConfigGenerator.generate_streamable_http_example_configs(
                service_name, alb_url, description
            )
        )

        instructions = f"""
# MCP Server Setup Instructions

Your MCP server '{service_name}' has been deployed successfully!
ALB URL: {alb_url}

## Configuration

**MCP Clients supports HTTP SSE (e.g. Claude Code):**

Add this configuration to your MCP client config file:
```json
{configs_sse}
```

**MCP Clients supports Streamable HTTP (e.g. Cline):**

Add this configuration to your MCP client config file:
```json
{configs_streamable_http}
```

## Testing the Connection

You can test the connection using MCP inspector:
```bash
npx @modelcontextprotocol/inspector --cli {alb_url}/mcp --method tools/list
```

## Troubleshooting

1. **Connection Issues:**
   - Verify the ALB URL is accessible: `curl -v {alb_url}/mcp`
   - Check your firewall/security groups

2. **Server Issues:**
   - Check ECS service health in AWS Console
   - Review CloudWatch logs for the service
"""

        return instructions
