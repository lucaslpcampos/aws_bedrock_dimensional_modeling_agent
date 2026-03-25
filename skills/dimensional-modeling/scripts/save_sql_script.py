"""
Save SQL Script — Persist generated SQL locally or to S3.

Usage:
    # Save locally (default)
    python save_sql_script.py --database DB --table TABLE --sql-file path/to/script.sql

    # Save to S3
    python save_sql_script.py --database DB --table TABLE --sql-file path/to/script.sql --s3 [--profile PROFILE]

    # Pass SQL content directly
    python save_sql_script.py --database DB --table TABLE --sql-content "SELECT ..." [--s3]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3


def resolve_s3_bucket(session):
    """Resolve the SQL scripts bucket from CloudFormation outputs."""
    cf = session.client("cloudformation")
    try:
        resp = cf.describe_stacks(StackName="DimModelingStorage")
        for output in resp["Stacks"][0].get("Outputs", []):
            if "SqlScripts" in output["OutputKey"] or "sql-scripts" in output.get("OutputValue", ""):
                return output["OutputValue"]
    except Exception:
        pass

    try:
        resp = cf.describe_stacks(StackName="DimModelingStorage")
        for output in resp["Stacks"][0].get("Outputs", []):
            if "Bucket" in output["OutputKey"]:
                value = output["OutputValue"]
                if "sql-scripts" in value:
                    return value
    except Exception:
        pass

    raise RuntimeError(
        "Could not resolve SQL scripts bucket from CloudFormation. "
        "Pass --bucket explicitly or check stack outputs."
    )


def save_local(database: str, table: str, sql_content: str, base_dir: str = "output/sql"):
    """Save SQL script to local filesystem."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = Path(base_dir) / database / table / f"{table}_{timestamp}.sql"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sql_content, encoding="utf-8")
    return {"status": "saved", "path": str(path)}


def save_s3(session, database: str, table: str, sql_content: str, bucket: str | None = None):
    """Save SQL script to S3."""
    if not bucket:
        bucket = resolve_s3_bucket(session)

    s3 = session.client("s3")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"scripts/{database}/{table}/{table}_{timestamp}.sql"

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=sql_content.encode("utf-8"),
        ContentType="text/plain; charset=utf-8",
    )

    s3_uri = f"s3://{bucket}/{key}"
    return {"status": "saved", "s3_uri": s3_uri, "bucket": bucket, "key": key}


def main():
    parser = argparse.ArgumentParser(description="Save generated SQL scripts")
    parser.add_argument("--database", required=True, help="Target database name")
    parser.add_argument("--table", required=True, help="Target table name")
    parser.add_argument("--profile", help="AWS profile name", default=None)
    parser.add_argument("--region", help="AWS region", default="us-east-1")

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--sql-file", help="Path to .sql file to save")
    source.add_argument("--sql-content", help="SQL content as string")

    parser.add_argument("--s3", action="store_true", help="Upload to S3 instead of local")
    parser.add_argument("--bucket", help="S3 bucket (auto-resolved from CloudFormation if omitted)")

    args = parser.parse_args()

    if args.sql_file:
        sql_content = Path(args.sql_file).read_text(encoding="utf-8")
    else:
        sql_content = args.sql_content

    if args.s3:
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        result = save_s3(session, args.database, args.table, sql_content, args.bucket)
    else:
        result = save_local(args.database, args.table, sql_content)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
