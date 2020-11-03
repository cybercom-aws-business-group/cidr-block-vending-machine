import logging as log
import cfnresponse
import os
import requests
import json
import boto3
from requests_aws_sign import AWSV4Sign

def send_request(payload, method):
    session = boto3.Session()
    credentials = session.get_credentials()
    # sigv4 credentials must be scoped to the correct api-gateway region. Parse region from 
    # cidr vending machine api - gateway endpoint : https://{api-id}.execute-api.{region}.amazonaws.com. 
    uri = os.environ['VENDING_MACHINE_API']
    region = uri.split('.')[2]
    headers={"Content-Type":"application/json"}
    service = 'execute-api'
    auth=AWSV4Sign(credentials, region, service)
    
    payload['region'] = session.region_name

    if method in ['POST', 'PATCH', 'DELETE']:
        if method == 'POST': response = requests.post(uri, auth=auth, headers=headers,params=payload)
        elif method == 'PATCH': response = requests.patch(uri, auth=auth, headers=headers,params=payload)
        elif method == 'DELETE': response = requests.delete(uri, auth=auth, headers=headers,params=payload)
        return response
    else:
        raise ValueError("Invalid HTTP method: {} ".format(method))

def handler(event, context):

    log.getLogger().setLevel(log.INFO)
    physical_id = 'MyCustomResource'

    try:
        log.info('Input event: %s', event)
        
        payload = {}
        attributes = {}        
        http_method = 'POST'

        # Check if this is a Update, Delete or Create
        if event['RequestType'] == 'Create' and event['ResourceProperties'].get('vpcId', False):
            http_method = 'PATCH'
            payload['cidr_block'] = event['ResourceProperties']['cidrBlock']
            payload['vpc_id'] = event['ResourceProperties']['vpcId']            
        elif event['RequestType'] == 'Delete' and event['ResourceProperties'].get('vpcId', False):
            http_method = 'DELETE'
            payload['cidr_block'] = event['ResourceProperties']['cidrBlock']
        elif event['RequestType'] == 'Delete':
            cfnresponse.send(event, context, cfnresponse.SUCCESS, attributes, physical_id)
            return            
            
        http_resp = send_request(payload, http_method)

        resp = json.loads(http_resp.text)
        log.info("http_response: {}".format(resp))

        cfnresponse.send(event, context, cfnresponse.SUCCESS, resp, physical_id)

    except Exception as e:
        log.exception(e)

        cfnresponse.send(event, context, cfnresponse.FAILED, {}, physical_id)