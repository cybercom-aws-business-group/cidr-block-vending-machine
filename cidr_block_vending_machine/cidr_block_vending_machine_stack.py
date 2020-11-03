from aws_cdk import (
    core,
    aws_iam,
    aws_lambda,
    aws_dynamodb,
    aws_apigateway
)


class CidrBlockVendingMachineStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        organization_id = self.node.try_get_context("organizationId")

        # create dynamo table
        allocation_table = aws_dynamodb.Table(
            self, "CidrBlockTable",
            partition_key=aws_dynamodb.Attribute(
                name="vpcCidrBlock",
                type=aws_dynamodb.AttributeType.STRING
            )
        )

        # create producer lambda function
        create_lambda = aws_lambda.Function(self, "create_lambda_function",
                                              runtime=aws_lambda.Runtime.PYTHON_3_6,
                                              handler="create.lambda_handler",
                                              code=aws_lambda.Code.asset("./src/"))

        create_lambda.add_environment("TABLE_NAME", allocation_table.table_name)
        create_lambda.add_environment("MASTER_CIDR_BLOCK", "10.0.0.0/12")
        create_lambda.add_environment("VPC_NETMASK", "24")
        create_lambda.add_environment("SUBNET_NETMASK", "26")

        # grant permission to lambda to write to demo table
        allocation_table.grant_write_data(create_lambda)
        allocation_table.grant_read_data(create_lambda)

        # API gateway ... Allow own Organizations
        api_policy = aws_iam.PolicyDocument()

        api_policy.add_statements(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                principals=[aws_iam.AnyPrincipal()],
                actions=["execute-api:Invoke"],
                resources=[core.Fn.join('', ['execute-api:/', '*'])]))

        api_policy.add_statements(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.DENY,
                actions=["execute-api:Invoke"],
                conditions={
                    "StringNotEquals": {
                        "aws:PrincipalOrgID": [
                            organization_id
                        ]
                    }
                },
                principals=[aws_iam.AnyPrincipal()],
                resources=[core.Fn.join('', ['execute-api:/', '*'])]))

        base_api = aws_apigateway.RestApi(self, 'ApiGateway', rest_api_name='cidr_vending_machine', policy=api_policy)

        vpc_api = base_api.root.add_resource('vpc')

        rest_api_role = aws_iam.Role(self,'RestAPIRole',
            assumed_by=aws_iam.ServicePrincipal('apigateway.amazonaws.com'),
            managed_policies=[aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess')]
        )
        
        patch_request_string = """
            {{
            "TableName": "{}",
                "Key": {{
                        "vpcCidrBlock": {{
                            "S": "$input.params('cidr_block')"
                        }}
                    }},
                    "UpdateExpression": "set vpcId = :v",
                    "ConditionExpression": "accountId = :v2",
                    "ExpressionAttributeValues" : {{
                        ":v": {{"S": "$input.params('vpc_id')"}},
                        ":v2": {{"S": "$context.identity.accountId"}}
                    }},
                    "ReturnValues": "ALL_NEW"

            }}"""

        delete_request_string = """
            {{
            "TableName": "{}",
                "Key": {{
                        "vpcCidrBlock": {{
                            "S": "$input.params('cidr_block')"
                        }}
                    }},
                "ConditionExpression": "accountId = :v2",
                "ExpressionAttributeValues" : {{
                    ":v2": {{"S": "$context.identity.accountId"}}
                }}
            }}"""


        network_integration = aws_apigateway.LambdaIntegration(create_lambda)
        update_integration = aws_apigateway.AwsIntegration(
            service='dynamodb',
            action='UpdateItem',
            integration_http_method='POST',
            options=aws_apigateway.IntegrationOptions(
                request_templates={
                    "application/json": patch_request_string.format(allocation_table.table_name)
                },
                integration_responses=[aws_apigateway.IntegrationResponse(
                    status_code="200"
                )],
                credentials_role=rest_api_role
            )
        )

        delete_integration = aws_apigateway.AwsIntegration(
            service='dynamodb',
            action='DeleteItem',
            integration_http_method='POST',
            options=aws_apigateway.IntegrationOptions(
                request_templates={
                    "application/json": delete_request_string.format(allocation_table.table_name)
                },
                integration_responses=[aws_apigateway.IntegrationResponse(
                    status_code="200"
                )],
                credentials_role=rest_api_role
            )
        )

        vpc_api.add_method('POST', network_integration, authorization_type=aws_apigateway.AuthorizationType.IAM)
        vpc_api.add_method('DELETE', delete_integration, authorization_type=aws_apigateway.AuthorizationType.IAM, 
            method_responses=[aws_apigateway.MethodResponse(status_code="200")])
        vpc_api.add_method('PATCH', update_integration,authorization_type=aws_apigateway.AuthorizationType.IAM,
            method_responses=[aws_apigateway.MethodResponse(status_code="200")])

