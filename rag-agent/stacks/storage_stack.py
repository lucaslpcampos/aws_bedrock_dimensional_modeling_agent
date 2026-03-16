"""
StorageStack
============
Provisions:
  - S3 bucket for source documents (PDF)
  - BucketDeployment to upload the Star Schema book
  - S3 Vectors bucket + index for storing embeddings

Outputs exposed to other stacks:
  - source_bucket   : the S3 docs bucket
  - vector_index_arn: ARN of the S3 Vectors index (consumed by KnowledgeBaseStack)
"""
import os
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_s3 as s3,
    aws_s3_deployment as s3d,
    aws_s3vectors as s3vectors,  # L1 only: CfnVectorBucket, CfnIndex
)
from config import settings


class StorageStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account = cdk.Stack.of(self).account
        region = cdk.Stack.of(self).region

        # ------------------------------------------------------------------
        # S3 bucket — stores the source PDF document
        # ------------------------------------------------------------------
        self.source_bucket = s3.Bucket(
            self,
            "DocsBucket",
            bucket_name=f"{settings.DOCS_BUCKET_NAME_PREFIX}-{account}-{region}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            auto_delete_objects=False,
        )

        # Upload the book PDF from the local ../book/ directory
        book_path = os.path.join(os.path.dirname(__file__), "..", "..", "book")
        s3d.BucketDeployment(
            self,
            "UploadBook",
            sources=[s3d.Source.asset(book_path)],
            destination_bucket=self.source_bucket,
            destination_key_prefix=settings.DOCS_S3_PREFIX,
        )

        # Upload business context documents (PDFs/Word) if the directory has files
        business_docs_path = os.path.join(
            os.path.dirname(__file__), "..", settings.BUSINESS_DOCS_LOCAL_PATH
        )
        if os.path.isdir(business_docs_path) and any(
            f for f in os.listdir(business_docs_path) if not f.startswith(".")
        ):
            s3d.BucketDeployment(
                self,
                "UploadBusinessDocs",
                sources=[s3d.Source.asset(business_docs_path)],
                destination_bucket=self.source_bucket,
                destination_key_prefix=settings.DOCS_S3_PREFIX,
            )

        # ------------------------------------------------------------------
        # S3 bucket — stores generated SQL scripts
        # ------------------------------------------------------------------
        self.sql_scripts_bucket = s3.Bucket(
            self,
            "SqlScriptsBucket",
            bucket_name=f"{settings.SQL_SCRIPTS_BUCKET_NAME_PREFIX}-{account}-{region}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            auto_delete_objects=False,
        )

        # ------------------------------------------------------------------
        # S3 Vectors — vector bucket + index for embeddings (L1 constructs)
        # ------------------------------------------------------------------
        vector_bucket_name = f"{settings.VECTOR_BUCKET_NAME_PREFIX}-{account}-{region}"

        vector_bucket = s3vectors.CfnVectorBucket(
            self,
            "VectorBucket",
            vector_bucket_name=vector_bucket_name,
        )
        vector_bucket.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

        vector_index = s3vectors.CfnIndex(
            self,
            "VectorIndex",
            vector_bucket_name=vector_bucket_name,
            index_name=settings.VECTOR_INDEX_NAME,
            dimension=settings.VECTOR_DIMENSION,
            distance_metric=settings.DISTANCE_METRIC,
            data_type="float32",  # required by Titan Embeddings V2
            # Mark chunk text fields as non-filterable to bypass the 2048-byte
            # filterable metadata limit. Bedrock KB stores the chunk text in
            # AMAZON_BEDROCK_TEXT_CHUNK which can easily exceed the limit.
            metadata_configuration=s3vectors.CfnIndex.MetadataConfigurationProperty(
                non_filterable_metadata_keys=[
                    "AMAZON_BEDROCK_TEXT_CHUNK",
                    "AMAZON_BEDROCK_METADATA",
                ]
            ),
        )
        vector_index.add_dependency(vector_bucket)

        # CloudFormation Outputs for reference
        cdk.CfnOutput(self, "DocsBucketName", value=self.source_bucket.bucket_name)
        cdk.CfnOutput(self, "SqlScriptsBucketName", value=self.sql_scripts_bucket.bucket_name)
        cdk.CfnOutput(self, "VectorBucketName", value=vector_bucket_name)
