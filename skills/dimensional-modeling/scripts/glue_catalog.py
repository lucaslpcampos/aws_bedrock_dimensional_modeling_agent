"""
Glue Catalog CLI — Standalone access to AWS Glue Data Catalog.

Provides the same 4 read-only functions as the Bedrock Agent Lambda,
but as a CLI tool for use within Claude Code.

Usage:
    python glue_catalog.py list-databases [--profile PROFILE] [--region REGION]
    python glue_catalog.py list-tables --database DB [--profile PROFILE] [--region REGION]
    python glue_catalog.py get-schema --database DB --table TABLE [--profile PROFILE] [--region REGION]
    python glue_catalog.py get-statistics --database DB --table TABLE [--profile PROFILE] [--region REGION]
"""

import argparse
import json
import sys

import boto3


def get_glue_client(profile: str | None, region: str):
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client("glue")


def list_databases(glue):
    databases = []
    paginator = glue.get_paginator("get_databases")
    for page in paginator.paginate():
        for db in page["DatabaseList"]:
            databases.append(
                {
                    "name": db["Name"],
                    "description": db.get("Description", ""),
                }
            )
    return {"databases": databases}


def list_tables(glue, database_name: str):
    tables = []
    paginator = glue.get_paginator("get_tables")
    for page in paginator.paginate(DatabaseName=database_name):
        for t in page["TableList"]:
            tables.append(
                {
                    "name": t["Name"],
                    "table_type": t.get("TableType", ""),
                    "description": t.get("Description", ""),
                    "columns_count": len(
                        t.get("StorageDescriptor", {}).get("Columns", [])
                    ),
                }
            )
    return {"database": database_name, "tables": tables}


def get_table_schema(glue, database_name: str, table_name: str):
    resp = glue.get_table(DatabaseName=database_name, Name=table_name)
    table = resp["Table"]
    sd = table.get("StorageDescriptor", {})

    columns = [
        {
            "name": c["Name"],
            "type": c["Type"],
            "comment": c.get("Comment", ""),
        }
        for c in sd.get("Columns", [])
    ]

    partition_keys = [
        {
            "name": p["Name"],
            "type": p["Type"],
            "comment": p.get("Comment", ""),
        }
        for p in table.get("PartitionKeys", [])
    ]

    return {
        "database": database_name,
        "table": table_name,
        "columns": columns,
        "partition_keys": partition_keys,
        "location": sd.get("Location", ""),
        "input_format": sd.get("InputFormat", ""),
        "output_format": sd.get("OutputFormat", ""),
        "serde": sd.get("SerdeInfo", {}).get("SerializationLibrary", ""),
        "table_type": table.get("TableType", ""),
        "parameters": table.get("Parameters", {}),
    }


def get_table_statistics(glue, database_name: str, table_name: str):
    resp = glue.get_table(DatabaseName=database_name, Name=table_name)
    table = resp["Table"]
    params = table.get("Parameters", {})

    stats = {
        "database": database_name,
        "table": table_name,
        "record_count": params.get("recordCount", "N/A"),
        "average_record_size": params.get("averageRecordSize", "N/A"),
        "size_bytes": params.get("sizeKey", params.get("totalSize", "N/A")),
        "num_files": params.get("numFiles", "N/A"),
    }

    try:
        col_names = [
            c["Name"]
            for c in table.get("StorageDescriptor", {}).get("Columns", [])
        ]
        if col_names:
            col_resp = glue.get_column_statistics_for_table(
                DatabaseName=database_name,
                TableName=table_name,
                ColumnNames=col_names[:100],
            )
            col_stats = []
            for cs in col_resp.get("ColumnStatisticsList", []):
                col_stats.append(
                    {
                        "column": cs["ColumnName"],
                        "type": cs["StatisticsData"]["Type"],
                    }
                )
            stats["column_statistics"] = col_stats
    except glue.exceptions.EntityNotFoundException:
        stats["column_statistics"] = "No column statistics available"
    except Exception as e:
        stats["column_statistics"] = f"Could not retrieve: {e}"

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="CLI for AWS Glue Data Catalog access"
    )
    parser.add_argument("--profile", help="AWS profile name", default=None)
    parser.add_argument("--region", help="AWS region", default="us-east-1")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-databases", help="List all Glue databases")

    lt = subparsers.add_parser("list-tables", help="List tables in a database")
    lt.add_argument("--database", required=True, help="Database name")

    gs = subparsers.add_parser("get-schema", help="Get full table schema")
    gs.add_argument("--database", required=True, help="Database name")
    gs.add_argument("--table", required=True, help="Table name")

    gt = subparsers.add_parser("get-statistics", help="Get table statistics")
    gt.add_argument("--database", required=True, help="Database name")
    gt.add_argument("--table", required=True, help="Table name")

    args = parser.parse_args()
    glue = get_glue_client(args.profile, args.region)

    if args.command == "list-databases":
        result = list_databases(glue)
    elif args.command == "list-tables":
        result = list_tables(glue, args.database)
    elif args.command == "get-schema":
        result = get_table_schema(glue, args.database, args.table)
    elif args.command == "get-statistics":
        result = get_table_statistics(glue, args.database, args.table)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
