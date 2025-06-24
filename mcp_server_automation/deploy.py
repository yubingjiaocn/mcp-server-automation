"""Deploy module for MCP server automation."""

import os
from typing import Optional

import boto3
from jinja2 import Template


class DeployCommand:
    """Handles ECS deployment with CloudFormation."""

    def execute(
        self,
        image_uri: str,
        service_name: str,
        cluster_name: str,
        aws_region: str,
        port: int,
        cpu: int,
        memory: int,
        vpc_id: str,
        alb_subnet_ids: list,
        ecs_subnet_ids: list,
        certificate_arn: Optional[str] = None,
    ) -> str:
        """Execute the deployment process."""

        # Generate CloudFormation template
        cf_template = self._generate_cloudformation_template(
            image_uri,
            service_name,
            cluster_name,
            port,
            cpu,
            memory,
            vpc_id,
            alb_subnet_ids,
            ecs_subnet_ids,
            certificate_arn,
        )

        # Deploy CloudFormation stack
        stack_name = f"mcp-server-{service_name}"
        alb_url = self._deploy_cloudformation_stack(
            cf_template,
            stack_name,
            aws_region,
            service_name,
            vpc_id,
            alb_subnet_ids,
            ecs_subnet_ids,
            certificate_arn,
        )

        return alb_url

    def _generate_cloudformation_template(
        self,
        image_uri: str,
        service_name: str,
        cluster_name: str,
        port: int,
        cpu: int,
        memory: int,
        vpc_id: str,
        alb_subnet_ids: list,
        ecs_subnet_ids: list,
        certificate_arn: Optional[str],
    ) -> str:
        """Generate CloudFormation template for ECS deployment."""

        # Load CloudFormation template
        template_path = os.path.join(
            os.path.dirname(__file__), "templates", "ecs-service.yaml"
        )
        with open(template_path, "r") as f:
            template_content = f.read()

        template = Template(template_content)
        return template.render(
            service_name=service_name,
            cluster_name=cluster_name,
            image_uri=image_uri,
            port=port,
            cpu=cpu,
            memory=memory,
        )

    def _deploy_cloudformation_stack(
        self,
        template: str,
        stack_name: str,
        aws_region: str,
        service_name: str,
        vpc_id: str,
        alb_subnet_ids: list,
        ecs_subnet_ids: list,
        certificate_arn: Optional[str],
    ) -> str:
        """Deploy CloudFormation stack and return ALB URL."""
        print(f"Deploying CloudFormation stack: {stack_name}")

        cf_client = boto3.client("cloudformation", region_name=aws_region)

        # Check if stack exists
        try:
            cf_client.describe_stacks(StackName=stack_name)
            stack_exists = True
        except cf_client.exceptions.ClientError:
            stack_exists = False

        # Prepare parameters
        parameters = [
            {"ParameterKey": "ServiceName", "ParameterValue": service_name},
            {"ParameterKey": "VpcId", "ParameterValue": vpc_id},
            {
                "ParameterKey": "ALBSubnetIds",
                "ParameterValue": ",".join(alb_subnet_ids),
            },
            {
                "ParameterKey": "ECSSubnetIds",
                "ParameterValue": ",".join(ecs_subnet_ids),
            },
        ]

        if certificate_arn:
            parameters.append(
                {"ParameterKey": "CertificateArn", "ParameterValue": certificate_arn}
            )

        if stack_exists:
            print("Updating existing stack...")
            try:
                cf_client.update_stack(
                    StackName=stack_name,
                    TemplateBody=template,
                    Parameters=parameters,
                    Capabilities=["CAPABILITY_NAMED_IAM"],
                )
                waiter = cf_client.get_waiter("stack_update_complete")
            except cf_client.exceptions.ClientError as e:
                if "No updates are to be performed" in str(e):
                    print("No updates needed - stack is already up to date")
                    waiter = None
                else:
                    raise
        else:
            print("Creating new stack...")
            cf_client.create_stack(
                StackName=stack_name,
                TemplateBody=template,
                Parameters=parameters,
                Capabilities=["CAPABILITY_NAMED_IAM"],
            )
            waiter = cf_client.get_waiter("stack_create_complete")

        # Wait for stack operation to complete with extended timeout
        if waiter:
            print("Waiting for stack operation to complete...")
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={
                    "Delay": 30,  # Check every 30 seconds
                    "MaxAttempts": 120,  # Wait up to 60 minutes (120 * 30 seconds)
                },
            )

        # Get ALB URL from stack outputs
        stack_info = cf_client.describe_stacks(StackName=stack_name)
        outputs = stack_info["Stacks"][0].get("Outputs", [])

        for output in outputs:
            if output["OutputKey"] == "ALBUrl":
                print("Stack deployment completed successfully")
                return output["OutputValue"]

        raise RuntimeError("ALB URL not found in stack outputs")
