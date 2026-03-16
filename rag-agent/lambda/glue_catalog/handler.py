"""
Glue Catalog Lambda — Action Group for Bedrock Agent
=====================================================
Read-only access to AWS Glue Data Catalog + SQL script persistence to S3.
Provides 5 functions: list_databases, list_tables, get_table_schema,
get_table_statistics, save_sql_script.

Response format follows Bedrock Agent Function Details specification.
"""
import json
import logging
import os
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

glue = boto3.client("glue")
s3 = boto3.client("s3")

SQL_SCRIPTS_BUCKET = os.environ.get("SQL_SCRIPTS_BUCKET", "")
SQL_SCRIPTS_PREFIX = os.environ.get("SQL_SCRIPTS_PREFIX", "scripts/")


def lambda_handler(event, context):
    logger.info("Event: %s", json.dumps(event))

    function_name = event.get("function", "")
    parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}

    try:
        if function_name == "list_databases":
            result = _list_databases()
        elif function_name == "list_tables":
            result = _list_tables(parameters["database_name"])
        elif function_name == "get_table_schema":
            result = _get_table_schema(
                parameters["database_name"], parameters["table_name"]
            )
        elif function_name == "get_table_statistics":
            result = _get_table_statistics(
                parameters["database_name"], parameters["table_name"]
            )
        elif function_name == "save_sql_script":
            result = _save_sql_script(
                parameters["database_name"],
                parameters["table_name"],
                parameters["sql_content"],
            )
        else:
            result = {"error": f"Unknown function: {function_name}"}
    except Exception as e:
        logger.exception("Error executing %s", function_name)
        result = {"error": str(e)}

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "function": function_name,
            "functionResponse": {
                "responseBody": {"TEXT": {"body": json.dumps(result, default=str)}}
            },
        },
    }


def _list_databases():
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


def _list_tables(database_name: str):
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


def _get_table_schema(database_name: str, table_name: str):
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


def _get_table_statistics(database_name: str, table_name: str):
    # Table-level parameters (row count, data size)
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

    # Column-level statistics
    try:
        col_names = [
            c["Name"]
            for c in table.get("StorageDescriptor", {}).get("Columns", [])
        ]
        if col_names:
            col_resp = glue.get_column_statistics_for_table(
                DatabaseName=database_name,
                TableName=table_name,
                ColumnNames=col_names[:100],  # API limit
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


def _save_sql_script(database_name: str, table_name: str, sql_content: str):
    if not SQL_SCRIPTS_BUCKET:
        return {"error": "SQL_SCRIPTS_BUCKET environment variable is not configured."}

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"{SQL_SCRIPTS_PREFIX}{database_name}/{table_name}/{table_name}_{timestamp}.sql"

    s3.put_object(
        Bucket=SQL_SCRIPTS_BUCKET,
        Key=key,
        Body=sql_content.encode("utf-8"),
        ContentType="text/plain; charset=utf-8",
    )

    s3_uri = f"s3://{SQL_SCRIPTS_BUCKET}/{key}"
    logger.info("SQL script saved to %s", s3_uri)

    return {
        "status": "saved",
        "s3_uri": s3_uri,
        "bucket": SQL_SCRIPTS_BUCKET,
        "key": key,
    }
