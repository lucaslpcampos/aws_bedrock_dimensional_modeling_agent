#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.storage_stack import StorageStack
from stacks.knowledge_base_stack import KnowledgeBaseStack
from stacks.agent_stack import AgentStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

storage = StorageStack(app, "DimModelingStorage", env=env)

kb = KnowledgeBaseStack(
    app,
    "DimModelingKB",
    source_bucket=storage.source_bucket,
    env=env,
)
kb.add_dependency(storage)

agent = AgentStack(
    app,
    "DimModelingAgent",
    knowledge_base_id=kb.knowledge_base_id,
    sql_scripts_bucket=storage.sql_scripts_bucket,
    env=env,
)
agent.add_dependency(kb)

app.synth()
