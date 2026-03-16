"""
KnowledgeBaseStack
==================
Provisions:
  - IAM execution role for the Bedrock Knowledge Base
  - Bedrock Knowledge Base (vector store = S3 Vectors)
  - Bedrock Data Source pointing to the S3 documents bucket

The KB uses FIXED_SIZE chunking (512 tokens, 50 overlap) — required because
S3 Vectors has a 1 KB metadata limit per vector, which hierarchical chunking exceeds.

Outputs exposed to other stacks:
  - knowledge_base_id : used by AgentStack to associate the KB
"""
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_iam as iam,
    aws_bedrock as bedrock,
    aws_s3 as s3,
)
from config import settings


class KnowledgeBaseStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        source_bucket: s3.IBucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account = cdk.Stack.of(self).account
        region = cdk.Stack.of(self).region

        # Build the S3 Vectors index ARN locally from settings constants.
        # Avoids a cross-stack CloudFormation export, which prevents updating
        # the index without first destroying the KB stack.
        vector_bucket_name = (
            f"{settings.VECTOR_BUCKET_NAME_PREFIX}-{account}-{region}"
        )
        vector_index_arn = (
            f"arn:aws:s3vectors:{region}:{account}:"
            f"bucket/{vector_bucket_name}/index/{settings.VECTOR_INDEX_NAME}"
        )

        # ------------------------------------------------------------------
        # IAM Role — Bedrock Knowledge Base execution role
        # ------------------------------------------------------------------
        kb_role = iam.Role(
            self,
            "KBExecutionRole",
            role_name=f"AmazonBedrockExecutionRoleForKnowledgeBase-{construct_id}",
            assumed_by=iam.ServicePrincipal(
                "bedrock.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": account},
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:{region}:{account}:knowledge-base/*"
                    },
                },
            ),
        )

        # Permission to invoke Titan Embeddings V2 for creating vectors
        kb_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockInvokeEmbeddingModel",
                actions=["bedrock:InvokeModel"],
                resources=[settings.EMBEDDING_MODEL_ARN],
            )
        )

        # Permission to read documents from the source S3 bucket
        kb_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3ReadSourceDocuments",
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    source_bucket.bucket_arn,
                    f"{source_bucket.bucket_arn}/*",
                ],
                conditions={
                    "StringEquals": {"aws:ResourceAccount": account}
                },
            )
        )

        # Permission to read/write vectors in S3 Vectors
        kb_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3VectorsAccess",
                actions=[
                    "s3vectors:PutVectors",
                    "s3vectors:GetVectors",
                    "s3vectors:DeleteVectors",
                    "s3vectors:QueryVectors",
                    "s3vectors:ListVectors",
                    "s3vectors:DescribeIndex",
                ],
                resources=[
                    vector_index_arn,
                    f"{vector_index_arn}/*",
                ],
            )
        )

        # ------------------------------------------------------------------
        # Bedrock Knowledge Base (L1 construct — no L2 available yet)
        #
        # IMPORTANT: explicit dependency on kb_role ensures CloudFormation
        # waits for the IAM role AND its inline policy to be fully created
        # before creating the KB (avoids s3vectors:QueryVectors 403 error).
        # ------------------------------------------------------------------
        kb = bedrock.CfnKnowledgeBase(
            self,
            "KnowledgeBase",
            name=settings.KB_NAME,
            description=settings.KB_DESCRIPTION,
            role_arn=kb_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=settings.EMBEDDING_MODEL_ARN,
                ),
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="S3_VECTORS",
                s3_vectors_configuration=bedrock.CfnKnowledgeBase.S3VectorsConfigurationProperty(
                    index_arn=vector_index_arn,
                ),
            ),
        )
        # Force KB to wait for the IAM role AND its attached policy
        kb.node.add_dependency(kb_role)

        # ------------------------------------------------------------------
        # Bedrock Data Source — S3 bucket with fixed-size chunking
        # ------------------------------------------------------------------
        bedrock.CfnDataSource(
            self,
            "DataSource",
            name=settings.DATA_SOURCE_NAME,
            knowledge_base_id=kb.ref,
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=source_bucket.bucket_arn,
                    inclusion_prefixes=[settings.DOCS_S3_PREFIX],
                ),
            ),
            vector_ingestion_configuration=bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                    chunking_strategy="FIXED_SIZE",
                    fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
                        max_tokens=settings.CHUNK_MAX_TOKENS,
                        overlap_percentage=int(
                            settings.CHUNK_OVERLAP_TOKENS / settings.CHUNK_MAX_TOKENS * 100
                        ),
                    ),
                ),
            ),
        )

        # Expose KB ID for AgentStack
        self.knowledge_base_id = kb.ref

        # CloudFormation Outputs for use in scripts
        cdk.CfnOutput(self, "KnowledgeBaseId", value=kb.ref)
        cdk.CfnOutput(self, "KBExecutionRoleArn", value=kb_role.role_arn)
