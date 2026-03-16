# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG-powered Bedrock Agent for dimensional modeling consulting, grounded in "Star Schema: The Complete Reference" by Christopher Adamson. The agent inspects AWS Glue Data Catalog schemas (silver layer) and proposes gold-layer dimensional models (DDL + ETL SQL) using a KPI-driven approach.

## Commands

```bash
# Deploy all stacks (Storage → KB → Agent)
cdk deploy

# Deploy a single stack
cdk deploy AgentStack

# Trigger knowledge base document ingestion (after deploy or after adding new docs)
python rag-agent/scripts/start_ingestion_job.py [--profile PROFILE]

# Check ingestion status
python rag-agent/scripts/check_ingestion_status.py [--profile PROFILE]

# Interactive chat with the agent (main way to test)
python rag-agent/scripts/demo_chat.py [--profile PROFILE] [--trace]

# Generate mock CSV data
python mock_data.py
```

## Architecture

Three CDK stacks deployed in dependency order:

**StorageStack** → S3 buckets (source docs, SQL scripts) + S3 Vectors (embeddings index, 1024-dim cosine)

**KnowledgeBaseStack** → Bedrock KB with Titan Embeddings V2, FIXED_SIZE chunking (300 tokens, 30 overlap — constrained by S3 Vectors 1KB metadata limit)

**AgentStack** → Bedrock Agent (Claude Sonnet 4 cross-region) + Lambda action group for Glue Catalog access + KB association

Stack outputs are consumed downstream: `source_bucket` → KB, `knowledge_base_id` → Agent. Scripts like `demo_chat.py` resolve IDs dynamically from CloudFormation outputs.

## Key Files

- `rag-agent/app.py` — CDK entry point, wires all 3 stacks
- `rag-agent/config/settings.py` — All constants (model IDs, chunk sizes, names). No hardcoding in stacks.
- `rag-agent/prompts/agent_instruction.txt` — Agent system prompt (KPI-driven workflow, aggregate table guidelines, SQL generation rules). Editing this file requires `cdk deploy AgentStack` to take effect.
- `rag-agent/lambda/glue_catalog/handler.py` — Action group Lambda: `list_databases`, `list_tables`, `get_table_schema`, `get_table_statistics`, `save_sql_script`
- `rag-agent/stacks/agent_stack.py` — Agent definition including action group function schemas (OpenAPI-style inline)

## Agent Prompt Design

The system prompt at `prompts/agent_instruction.txt` follows a KPI-driven workflow: gather indicators first, clarify ambiguous metrics, inspect silver tables, map indicators to model elements, then propose DDL with aggregate fact tables when warranted. Changes to agent behavior go here. The prompt is English; the agent responds in the user's language.

## Conventions

- **SQL output**: ANSI SQL, Apache Iceberg format (`TBLPROPERTIES ('table_type'='ICEBERG')`)
- **Surrogate keys**: `BIGINT AUTO_INCREMENT` for dimensions
- **SCD Type 2**: `effective_date`, `expiry_date`, `is_current` columns
- **Aggregate fact tables**: Named `fact_<process>_<grain>`, populated from base fact (not silver)
- **IAM**: Least privilege per component; agent role uses `SourceAccount` conditions
- **Region**: `us-east-1` (Bedrock Agents requirement)

## Language Preference

Always respond in Português (BR). Always use the `aws-documentation-mcp-server` MCP tool for AWS documentation questions.
