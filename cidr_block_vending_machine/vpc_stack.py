from aws_cdk import (
    core,
    aws_ec2,
    aws_iam,
    aws_lambda,
)

from aws_cdk.aws_lambda_python import PythonFunction

class VpcStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ipam_endpoint = self.node.try_get_context("apiEndpoint") + "vpc"

        custom_resource_handler = PythonFunction(self, "CreateLambda",
            entry="./src_custom_resource", 
            runtime=aws_lambda.Runtime.PYTHON_3_6
            )
        custom_resource_handler.add_environment("VENDING_MACHINE_API", ipam_endpoint)

# By default Lambda execution role doesn't allow cross-account API invoke
        custom_resource_handler.role.add_to_policy(aws_iam.PolicyStatement(
            resources=["*"],
            actions=["execute-api:Invoke"]
            ))

# First Custom Resource, get free CIDR from the Vending Machine
        cr_create = core.CustomResource(self, "Resource1", 
            resource_type="Custom::GetSubnet", 
            service_token=custom_resource_handler.function_arn
            )
# Then provision a new VPC with private subnets to the given CIDR range
# NOTE: we are using L1 construct for VPC. L2 construct didn't work with custom resources.
        cidr = cr_create.get_att("vpcCidrBlock").to_string()
        subnet0_cidr = cr_create.get_att("subnet0CidrBlock").to_string()
        subnet1_cidr = cr_create.get_att("subnet1CidrBlock").to_string()
        subnet2_cidr = cr_create.get_att("subnet2CidrBlock").to_string()
        subnet3_cidr = cr_create.get_att("subnet3CidrBlock").to_string()
        
        vpc = aws_ec2.CfnVPC(self, "VPC", cidr_block=cidr)

        aws_ec2.CfnSubnet(self, "Private0", 
            vpc_id=vpc.ref, 
            cidr_block=subnet0_cidr)

        aws_ec2.CfnSubnet(self, "Private1", 
            vpc_id=vpc.ref, 
            cidr_block=subnet1_cidr)

        aws_ec2.CfnSubnet(self, "Private2", 
            vpc_id=vpc.ref, 
            cidr_block=subnet2_cidr)

        aws_ec2.CfnSubnet(self, "Private3", 
            vpc_id=vpc.ref, 
            cidr_block=subnet3_cidr)


# Lastly update the Vpc Id to the Vending Machine
        cr_update = core.CustomResource(self, "Resource2", 
            resource_type="Custom::PutVpcId", 
            properties={
                "vpcId":vpc.ref,
                "cidrBlock":cidr
            },
            service_token=custom_resource_handler.function_arn
            )

        core.CfnOutput(self, "cidrBlock", value=cidr)