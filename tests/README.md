# Unit Tests for MCP Convert Automate

This directory contains comprehensive unit tests for the MCP Server Automation CLI tool, covering all non-AWS and non-Docker functionality.

## Test Coverage

### 1. Command Generation Tests (`test_build_command_generation.py`)
- **Entrypoint Command Generation**: Tests the `_generate_entrypoint_command` function that creates mcp-proxy commands
  - Single commands, commands with arguments, proper `--` separator usage
  - Format: `mcp-proxy --debug --port 8000 --shell <command> -- <args>`
- **Image Tag Generation**: Tests dynamic Docker image tag creation using GitHub API
- **README Command Extraction**: Tests parsing MCP server configurations from README files

### 2. Configuration Tests (`test_config.py`) 
- **YAML Config Parsing**: Tests loading and parsing of YAML configuration files
- **Build Configuration**: Tests parsing of build settings including new features:
  - `command_override`: Override for MCP bootstrap commands
  - `environment_variables`: Custom environment variables for Docker images
- **Deploy Configuration**: Tests deployment settings and subnet configurations
- **Image URI Parsing**: Tests parsing Docker image URIs into components

### 3. Package Detection Tests (`test_package_detection.py`)
- **Package Manager Detection**: Tests identification of different Python package managers
  - pip with requirements.txt
  - uv with pyproject.toml
  - poetry with pyproject.toml
  - setup.py installations
- **Command Override**: Tests that custom commands take precedence over auto-detection
- **Fallback Detection**: Tests detection of common server file patterns

### 4. Dockerfile Generation Tests (`test_dockerfile_generation.py`)
- **Template Rendering**: Tests Dockerfile generation without actual Docker builds
- **Package Manager Support**: Tests different installation methods in generated Dockerfiles
- **Environment Variables**: Tests injection of custom environment variables
- **Command Override**: Tests that custom commands are properly formatted in ENTRYPOINT

### 5. MCP Config Generation Tests (`test_mcp_config.py`)
- **Client Configuration**: Tests generation of MCP client configurations
  - SSE transport for Claude Code
  - HTTP transport for Cline
- **Setup Instructions**: Tests generation of deployment setup documentation
- **Edge Cases**: Tests handling of special characters, URLs with paths, etc.

## Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
python -m unittest discover tests -v

# Run specific test file
python -m unittest tests.test_config -v

# Run specific test
python -m unittest tests.test_config.TestConfigParsing.test_parse_basic_build_config -v
```

## Test Statistics

- **Total Tests**: 59
- **Test Files**: 5
- **Coverage**: Non-AWS, non-Docker functionality
- **Mocking**: Uses unittest.mock for external dependencies and file system operations

## Key Features Tested

### New Command Override Feature
- Tests that `command_override` in configuration takes precedence
- Validates proper mcp-proxy command formatting with `--` separator
- Ensures command and arguments are correctly split

### New Environment Variables Feature  
- Tests injection of custom environment variables into Docker images
- Validates ENV directive generation in Dockerfiles
- Tests configuration parsing and validation

### Core Functionality
- GitHub repository analysis and command detection
- Multiple package manager support (pip, uv, poetry, setup.py)
- Dockerfile template rendering with Jinja2
- Configuration file parsing and validation
- MCP client configuration generation

All tests pass successfully and provide comprehensive coverage of the tool's core functionality without requiring actual AWS resources or Docker builds.