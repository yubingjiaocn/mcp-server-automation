#!/usr/bin/env python3
"""
MCP Server Automation CLI

This CLI automates the process of transforming MCP stdio servers to Docker images
deployed on AWS ECS using mcp-proxy.
"""

import click
from .build import BuildCommand
from .deploy import DeployCommand
from .config import ConfigLoader


@click.command()
@click.version_option()
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="YAML configuration file path",
)
def cli(config):
    """Build MCP server Docker image and optionally deploy to ECS."""
    mcp_config = ConfigLoader.load_config(config)

    if not mcp_config.build:
        click.echo("Error: No 'build' section found in configuration file")
        return

    build_config = mcp_config.build
    deploy_config = mcp_config.deploy

    # Validate deployment requirements
    if deploy_config and deploy_config.enabled:
        if not build_config.push_to_ecr:
            click.echo("Error: deploy.enabled requires build.push_to_ecr to be true")
            return

        if (
            not deploy_config.service_name
            or not deploy_config.cluster_name
            or not deploy_config.vpc_id
        ):
            click.echo(
                "Error: deploy.enabled requires service_name, cluster_name, and vpc_id"
            )
            return

        # Validate subnet configuration
        if not deploy_config.alb_subnet_ids or not deploy_config.ecs_subnet_ids:
            click.echo(
                "Error: deploy.enabled requires both alb_subnet_ids and ecs_subnet_ids"
            )
            return
        
        if len(deploy_config.alb_subnet_ids) < 2:
            click.echo(
                "Error: deploy.enabled requires at least 2 ALB subnet IDs for load balancer"
            )
            return
        
        if len(deploy_config.ecs_subnet_ids) < 1:
            click.echo(
                "Error: deploy.enabled requires at least 1 ECS subnet ID for tasks"
            )
            return

    # Validate build requirements
    if build_config.push_to_ecr and not build_config.ecr_repository:
        click.echo("Error: ecr_repository is required when push_to_ecr is true")
        return

    # Execute build
    click.echo("Starting build process...")
    build_cmd = BuildCommand()
    build_cmd.execute(
        github_url=build_config.github_url,
        subfolder=build_config.subfolder,
        image_name=build_config.image_name,
        ecr_repository=build_config.ecr_repository,
        aws_region=build_config.aws_region,
        dockerfile_path=build_config.dockerfile_path,
        push_to_ecr=build_config.push_to_ecr,
        branch=build_config.branch,
        command_override=build_config.command_override,
        environment_variables=build_config.environment_variables,
    )

    # Execute deployment if enabled
    if deploy_config and deploy_config.enabled:
        click.echo("Starting deployment process...")

        # Use the image_uri from build config (always available now)
        image_uri = build_config.image_uri

        deploy_cmd = DeployCommand()
        alb_url = deploy_cmd.execute(
            image_uri=image_uri,
            service_name=deploy_config.service_name,
            cluster_name=deploy_config.cluster_name,
            aws_region=deploy_config.aws_region,
            port=deploy_config.port,
            cpu=deploy_config.cpu,
            memory=deploy_config.memory,
            vpc_id=deploy_config.vpc_id,
            alb_subnet_ids=deploy_config.alb_subnet_ids,
            ecs_subnet_ids=deploy_config.ecs_subnet_ids,
            certificate_arn=deploy_config.certificate_arn,
        )

        # Generate MCP configuration (always)
        from .mcp_config import MCPConfigGenerator

        config = MCPConfigGenerator.print_setup_instructions(
            deploy_config.service_name, alb_url
        )

        # Print configuration to stdout
        click.echo("\nMCP Client Configuration:")
        click.echo(config)

        # Save to file if requested
        if deploy_config.save_config:
            MCPConfigGenerator.save_config(config, deploy_config.save_config)
            click.echo(
                f"\nMCP configuration guide saved to: {deploy_config.save_config}"
            )

        click.echo(f"\nDeployment successful! ALB URL: {alb_url}")
    else:
        click.echo(
            "Build completed successfully! (Deployment skipped - deploy.enabled is false)"
        )


if __name__ == "__main__":
    cli()
