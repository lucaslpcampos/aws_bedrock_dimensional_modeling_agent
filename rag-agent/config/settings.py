"""Centralized configuration for the Dimensional Modeling RAG Agent."""

# AWS Region — Bedrock Agents GA in us-east-1
AWS_REGION = "us-east-1"

# --- Embedding Model ---
# Amazon Titan Embeddings V2 (supported by Bedrock KB + S3 Vectors)
EMBEDDING_MODEL_ARN = (
    "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
)

# --- LLM Model ---
# Claude Sonnet 4 via cross-region inference profile
# Cross-region profile provides higher throughput and automatic failover
AGENT_FOUNDATION_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"

# --- S3 Vectors ---
VECTOR_DIMENSION = 1024          # Titan Embeddings V2 default dimension
DISTANCE_METRIC = "cosine"       # Best for semantic similarity
VECTOR_BUCKET_NAME_PREFIX = "dim-modeling-vectors"
VECTOR_INDEX_NAME = "dim-modeling-index-v2"

# --- S3 Documents Bucket ---
DOCS_BUCKET_NAME_PREFIX = "dim-modeling-docs"
DOCS_S3_PREFIX = "documents/"

# --- Chunking ---
# S3 Vectors has a 2048-byte limit for filterable metadata. Bedrock KB treats
# AMAZON_BEDROCK_TEXT_CHUNK as filterable regardless of nonFilterableMetadataKeys.
# At ~5 bytes/word and ~1.3 words/token, 300 tokens ≈ 1950 bytes — safely under the limit.
CHUNK_MAX_TOKENS = 300
CHUNK_OVERLAP_TOKENS = 30

# --- Knowledge Base ---
KB_NAME = "dim-modeling-knowledge-base"
KB_DESCRIPTION = (
    "Contains the full text of 'Star Schema: The Complete Reference' "
    "by Christopher Adamson. Use this to answer all dimensional modeling questions."
)
DATA_SOURCE_NAME = "star-schema-book-v2"

# --- Bedrock Agent ---
AGENT_NAME = "dimensional-modeling-agent"
AGENT_DESCRIPTION = (
    "Expert consultant in dimensional modeling and data warehouse design, "
    "grounded in 'Star Schema: The Complete Reference' by Christopher Adamson."
)
AGENT_ALIAS_NAME = "prod"

# Number of KB chunks retrieved per query
MAX_RESULTS = 5

# --- Action Group (Glue Catalog) ---
ACTION_GROUP_NAME = "GlueCatalogAccess"
ACTION_GROUP_DESCRIPTION = (
    "Read-only access to AWS Glue Data Catalog. Use these functions to discover "
    "databases, list tables, inspect schemas, and retrieve table statistics."
)
GLUE_LAMBDA_TIMEOUT_SECONDS = 30
GLUE_LAMBDA_MEMORY_MB = 256

# --- S3 SQL Scripts (generated artifacts) ---
SQL_SCRIPTS_BUCKET_NAME_PREFIX = "dim-modeling-sql-scripts"
SQL_SCRIPTS_S3_PREFIX = "scripts/"

# --- Business Docs ---
BUSINESS_DOCS_LOCAL_PATH = "business_docs"
