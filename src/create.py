from __future__ import print_function

import json
import uuid
import time
import datetime
import decimal
import os
import boto3
import ipaddress

# Get the service resource.
dynamodb = boto3.resource('dynamodb')

# set environment variable
TABLE_NAME = os.environ['TABLE_NAME']
CIDR_BLOCK = os.environ['MASTER_CIDR_BLOCK']
VPC_NETMASK = os.environ['VPC_NETMASK']
SUBNET_NETMASK = os.environ['SUBNET_NETMASK']

def lambda_handler(event, context):
    block = ipaddress.ip_network(CIDR_BLOCK)
    table = dynamodb.Table(TABLE_NAME)

    for cidr in block.subnets(new_prefix=int(VPC_NETMASK)):

        response = table.get_item(Key={'vpcCidrBlock': str(cidr)})
        account_id = event['requestContext']['identity']['accountId']
        vpc_region = event['queryStringParameters']['region']

        if 'Item' not in response:
            item = {
                'vpcCidrBlock': str(cidr),
                'createdAt': str(datetime.datetime.now()),
                'accountId': account_id,
                'vpcRegion': vpc_region,
            }
# Calculate subnets
            subnets = cidr.subnets(new_prefix=int(SUBNET_NETMASK))
            
            for idx,subnet in enumerate(subnets):
                item["subnet"+str(idx)+"CidrBlock"] = str(subnet)

            table.put_item(Item=item)
            break

    return {
        'statusCode': 200,
        'body': json.dumps(item)
    }