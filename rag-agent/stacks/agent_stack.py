"""
AgentStack
==========
Provisions:
  - IAM execution role for the Bedrock Agent
  - Lambda function for Glue Data Catalog access (read-only)
  - Bedrock Agent with the dimensional modeling system prompt
  - Knowledge Base association (agent <-> KB)
  - Action Group for Glue Catalog (Lambda-backed, Function Details)
  - Agent Alias "prod" — required to invoke the agent via API

The system prompt is loaded from prompts/agent_instruction.txt so it can be
edited without touching Python code.
"""
import os
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    Duration,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_bedrock as bedrock,
)
from config import settings


def _load_instruction() -> str:
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "agent_instruction.txt"
    )
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


class AgentStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        knowledge_base_id: str,
        sql_scripts_bucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account = cdk.Stack.of(self).account
        region = cdk.Stack.of(self).region

        # ------------------------------------------------------------------
        # IAM Role — Bedrock Agent execution role
        # ------------------------------------------------------------------
        agent_role = iam.Role(
            self,
            "AgentExecutionRole",
            role_name=f"AmazonBedrockExecutionRoleForAgents-{construct_id}",
            assumed_by=iam.ServicePrincipal(
                "bedrock.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": account},
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:{region}:{account}:agent/*"
                    },
                },
            ),
        )

        # Permission to invoke the foundation model via cross-region inference profile.
        # The model ID "us.anthropic.claude-sonnet-4-..." is an inference profile,
        # so we need permissions on both the inference profile ARN and the
        # underlying foundation model ARN (without the "us." prefix).
        base_model_id = settings.AGENT_FOUNDATION_MODEL.split(".", 1)[1]  # strip region prefix

        agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowInvokeFoundationModel",
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    # Inference profile ARN
                    f"arn:aws:bedrock:{region}:{account}:inference-profile/{settings.AGENT_FOUNDATION_MODEL}",
                    # Foundation model ARN (all regions for cross-region routing)
                    f"arn:aws:bedrock:*::foundation-model/{base_model_id}",
                ],
            )
        )

        # Permission to resolve the inference profile
        agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowGetInferenceProfile",
                actions=["bedrock:GetInferenceProfile"],
                resources=[
                    f"arn:aws:bedrock:{region}:{account}:inference-profile/{settings.AGENT_FOUNDATION_MODEL}",
                ],
            )
        )

        # Permission to query the Knowledge Base
        agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockKnowledgeBaseAccess",
                actions=[
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate",
                ],
                resources=[
                    f"arn:aws:bedrock:{region}:{account}:knowledge-base/{knowledge_base_id}"
                ],
            )
        )

        # ------------------------------------------------------------------
        # Lambda — Glue Data Catalog access (read-only)
        # ------------------------------------------------------------------
        glue_lambda = _lambda.Function(
            self,
            "GlueCatalogLambda",
            function_name="bedrock-agent-glue-catalog",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join(os.path.dirname(__file__), "..", "lambda", "glue_catalog")
            ),
            timeout=Duration.seconds(settings.GLUE_LAMBDA_TIMEOUT_SECONDS),
            memory_size=settings.GLUE_LAMBDA_MEMORY_MB,
            environment={
                "SQL_SCRIPTS_BUCKET": sql_scripts_bucket.bucket_name,
                "SQL_SCRIPTS_PREFIX": settings.SQL_SCRIPTS_S3_PREFIX,
            },
        )

        # Glue read-only permissions
        glue_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="GlueReadOnly",
                actions=[
                    "glue:GetDatabases",
                    "glue:GetDatabase",
                    "glue:GetTables",
                    "glue:GetTable",
                    "glue:GetPartitions",
                    "glue:GetColumnStatisticsForTable",
                ],
                resources=[
                    f"arn:aws:glue:{region}:{account}:catalog",
                    f"arn:aws:glue:{region}:{account}:database/*",
                    f"arn:aws:glue:{region}:{account}:table/*/*",
                ],
            )
        )

        # S3 write permissions for saving SQL scripts
        sql_scripts_bucket.grant_put(glue_lambda)

        # Allow Bedrock Agent to invoke this Lambda
        glue_lambda.add_permission(
            "BedrockInvoke",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            source_arn=f"arn:aws:bedrock:{region}:{account}:agent/*",
        )

        # ------------------------------------------------------------------
        # Bedrock Agent (L1 construct)
        # KB association + Action Group inline
        # ------------------------------------------------------------------
        agent = bedrock.CfnAgent(
            self,
            "Agent",
            agent_name=settings.AGENT_NAME,
            description=settings.AGENT_DESCRIPTION,
            agent_resource_role_arn=agent_role.role_arn,
            foundation_model=settings.AGENT_FOUNDATION_MODEL,
            instruction=_load_instruction(),
            idle_session_ttl_in_seconds=1800,
            auto_prepare=True,
            knowledge_bases=[
                bedrock.CfnAgent.AgentKnowledgeBaseProperty(
                    knowledge_base_id=knowledge_base_id,
                    description=settings.KB_DESCRIPTION,
                    knowledge_base_state="ENABLED",
                )
            ],
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name=settings.ACTION_GROUP_NAME,
                    description=settings.ACTION_GROUP_DESCRIPTION,
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=glue_lambda.function_arn,
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="list_databases",
                                description="Lists all databases in the AWS Glue Data Catalog with their names and descriptions.",
                            ),
                            bedrock.CfnAgent.FunctionProperty(
                                name="list_tables",
                                description="Lists all tables in a specified Glue database with name, type, description, and column count.",
                                parameters={
                                    "database_name": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Name of the Glue database to list tables from.",
                                        required=True,
                                    ),
                                },
                            ),
                            bedrock.CfnAgent.FunctionProperty(
                                name="get_table_schema",
                                description="Returns the full schema of a table including columns (name, type, comment), partition keys, storage location, format, and SerDe information.",
                                parameters={
                                    "database_name": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Name of the Glue database containing the table.",
                                        required=True,
                                    ),
                                    "table_name": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Name of the table to get schema for.",
                                        required=True,
                                    ),
                                },
                            ),
                            bedrock.CfnAgent.FunctionProperty(
                                name="get_table_statistics",
                                description="Returns table-level statistics such as row count, data size, number of files, and column-level statistics when available.",
                                parameters={
                                    "database_name": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Name of the Glue database containing the table.",
                                        required=True,
                                    ),
                                    "table_name": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Name of the table to get statistics for.",
                                        required=True,
                                    ),
                                },
                            ),
                            bedrock.CfnAgent.FunctionProperty(
                                name="save_sql_script",
                                description="Saves a SQL SELECT script to S3. Use this after generating the SQL that populates a gold-layer dimensional model table. Returns the S3 URI of the saved file.",
                                parameters={
                                    "database_name": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Name of the target gold-layer database.",
                                        required=True,
                                    ),
                                    "table_name": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Name of the gold-layer table this SQL populates.",
                                        required=True,
                                    ),
                                    "sql_content": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="The complete SQL SELECT statement to save.",
                                        required=True,
                                    ),
                                },
                            ),
                        ],
                    ),
                ),
            ],
        )

        # ------------------------------------------------------------------
        # Agent Alias "prod" — required for programmatic invocation
        # ------------------------------------------------------------------
        alias = bedrock.CfnAgentAlias(
            self,
            "AgentAlias",
            agent_id=agent.ref,
            agent_alias_name=settings.AGENT_ALIAS_NAME,
        )
        alias.add_dependency(agent)

        # CloudFormation Outputs for use in scripts
        cdk.CfnOutput(self, "AgentId", value=agent.ref)
        cdk.CfnOutput(
            self,
            "AgentAliasId",
            value=cdk.Fn.select(1, cdk.Fn.split("|", alias.ref)),
        )
