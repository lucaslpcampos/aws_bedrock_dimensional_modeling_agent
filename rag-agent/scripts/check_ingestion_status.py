"""
check_ingestion_status.py
=========================
Polls the most recent Bedrock Knowledge Base ingestion job until it
reaches a terminal state (COMPLETE or FAILED).

Usage:
    python scripts/check_ingestion_status.py [--profile PROFILE]
"""
import argparse
import sys
import time
import boto3


def get_stack_output(cf_client, stack_name: str, output_key: str) -> str:
    response = cf_client.describe_stacks(StackName=stack_name)
    outputs = response["Stacks"][0].get("Outputs", [])
    for output in outputs:
        if output["OutputKey"] == output_key:
            return output["OutputValue"]
    raise ValueError(f"Output '{output_key}' not found in stack '{stack_name}'")


def main():
    parser = argparse.ArgumentParser(description="Poll Bedrock KB ingestion status")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--interval", type=int, default=10, help="Poll interval in seconds")
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    cf = session.client("cloudformation")
    bedrock_agent = session.client("bedrock-agent")

    kb_id = get_stack_output(cf, "DimModelingKB", "KnowledgeBaseId")

    ds_response = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id)
    ds_id = ds_response["dataSourceSummaries"][0]["dataSourceId"]

    # Get the most recent ingestion job
    jobs_response = bedrock_agent.list_ingestion_jobs(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
        sortBy={"attribute": "STARTED_AT", "order": "DESCENDING"},
    )
    jobs = jobs_response.get("ingestionJobSummaries", [])
    if not jobs:
        print("No ingestion jobs found. Run start_ingestion_job.py first.")
        sys.exit(1)

    job_id = jobs[0]["ingestionJobId"]
    print(f"Monitoring job {job_id} for KB {kb_id}...\n")

    terminal_states = {"COMPLETE", "FAILED", "STOPPED"}
    while True:
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=job_id,
        )
        job = response["ingestionJob"]
        status = job["status"]
        stats = job.get("statistics", {})

        print(
            f"[{status}] "
            f"Scanned: {stats.get('numberOfDocumentsScanned', 0)}  "
            f"Indexed: {stats.get('numberOfNewDocumentsIndexed', 0)}  "
            f"Updated: {stats.get('numberOfModifiedDocumentsIndexed', 0)}  "
            f"Failed: {stats.get('numberOfDocumentsFailed', 0)}"
        )

        if status in terminal_states:
            if status == "COMPLETE":
                print("\nIngestion completed successfully!")
                print(f"Total chunks indexed: {stats.get('numberOfNewDocumentsIndexed', 0)}")
            else:
                print(f"\nIngestion ended with status: {status}")
                failures = job.get("failureReasons", [])
                if failures:
                    print("Failure reasons:")
                    for reason in failures:
                        print(f"  - {reason}")
                sys.exit(1)
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
