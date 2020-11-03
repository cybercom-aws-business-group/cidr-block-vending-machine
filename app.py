#!/usr/bin/env python3

from aws_cdk import core

from cidr_block_vending_machine.cidr_block_vending_machine_stack import CidrBlockVendingMachineStack
from cidr_block_vending_machine.vpc_stack import VpcStack

app = core.App()
CidrBlockVendingMachineStack(app, "cidr-block-vending-machine")

VpcStack(app, "test-vpc-1")
VpcStack(app, "test-vpc-2")

app.synth()
