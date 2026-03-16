"""
start_ingestion_job.py
======================
Triggers a Bedrock Knowledge Base ingestion job to index the PDF stored in S3.

Bedrock does NOT automatically ingest documents after deployment.
Run this script once after `cdk deploy DimModelingKB` and again
any time the source PDF is updated.

Usage:
    python scripts/start_ingestion_job.py [--profile PROFILE]

Requirements:
    - AWS credentials configured (default profile or --profile)
    - CDK stacks DimModelingStorage and DimModelingKB must be deployed
"""
import argparse
import sys
import boto3


def get_stack_output(cf_client, stack_name: str, output_key: str) -> str:
    """Retrieve a CloudFormation stack output value."""
    response = cf_client.describe_stacks(StackName=stack_name)
    outputs = response["Stacks"][0].get("Outputs", [])
    for output in outputs:
        if output["OutputKey"] == output_key:
            return output["OutputValue"]
    raise ValueError(f"Output '{output_key}' not found in stack '{stack_name}'")


def main():
    parser = argparse.ArgumentParser(description="Trigger Bedrock KB ingestion job")
    parser.add_argument("--profile", default=None, help="AWS profile name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    cf = session.client("cloudformation")
    bedrock_agent = session.client("bedrock-agent")

    print("Fetching stack outputs...")
    try:
        kb_id = get_stack_output(cf, "DimModelingKB", "KnowledgeBaseId")
    except Exception as e:
        print(f"ERROR: Could not retrieve Knowledge Base ID from CloudFormation: {e}")
        print("Make sure `cdk deploy DimModelingKB` completed successfully.")
        sys.exit(1)

    # List data sources to get the data source ID
    ds_response = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id)
    data_sources = ds_response.get("dataSourceSummaries", [])
    if not data_sources:
        print("ERROR: No data sources found for this Knowledge Base.")
        sys.exit(1)

    ds_id = data_sources[0]["dataSourceId"]
    ds_name = data_sources[0]["name"]

    print(f"Knowledge Base ID : {kb_id}")
    print(f"Data Source ID    : {ds_id} ({ds_name})")
    print("Starting ingestion job...")

    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
    )

    job = response["ingestionJob"]
    print(f"\nIngestion job started successfully!")
    print(f"  Job ID  : {job['ingestionJobId']}")
    print(f"  Status  : {job['status']}")
    print(f"\nRun check_ingestion_status.py to monitor progress.")


if __name__ == "__main__":
    main()
